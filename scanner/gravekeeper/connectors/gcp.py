"""Read-only GCP IAM connector.

Inventories the service accounts in a single GCP project: their user-managed keys
(for a creation date), the project-level IAM roles each is bound to (to judge
over-privilege), and an owner drawn from the account description or a label.

READ-ONLY GUARANTEE
-------------------
Every call is a list/get against the IAM (and resource IAM policy) API. The
connector issues no create/update/delete/set call. `_READ_ONLY_METHODS` documents
the exact allow-list, which mirrors the least-privilege role we hand users:
    projects.serviceAccounts.list
    projects.serviceAccounts.keys.list
    projects.getIamPolicy

Credentials (per scan):
    {
        "project_id": "my-project",
        "service_account_json": { ...the SA key JSON as a dict... },
    }
`service_account_json` is the full contents of a Google service-account key file
(the object with "type", "private_key", "client_email", ...). It is only used to
build a read-only client; nothing is persisted.

LAST-ACTIVITY LIMITATION
------------------------
GCP exposes no cheap, universal "last used" timestamp for a service account. The
authoritative signals (key last-authentication, Policy Analyzer, Activity/Audit
logs) each need extra APIs, elevated scopes, or a data-access log pipeline that a
read-only inventory pass cannot assume. We therefore leave `last_activity_at` as
None, which the scorer treats as "never used" — for an aged account that surfaces
it as a never-used-but-old zombie candidate rather than hiding it.
"""

from __future__ import annotations

from datetime import datetime

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from ..models import AgentRecord, IdentityType, OwnerStatus, Source
from ._util import parse_iso8601 as _parse
from .base import Connector, ConnectorError

# The complete set of API methods this connector uses. All are list/get.
_READ_ONLY_METHODS = (
    "projects.serviceAccounts.list",
    "projects.serviceAccounts.keys.list",
    "projects.getIamPolicy",
)

_PAGE_SIZE = 100
_MAX_PAGES = 50  # cap paging breadth for a first pass; surfaced, never silent
_HTTP_TIMEOUT = 30  # seconds; httplib2's default is None (can hang forever)
# Labels/description keys we accept as naming an owner, in priority order.
_OWNER_LABEL_KEYS = ("owner", "created_by", "createdby", "team")
_READ_ONLY_SCOPE = "https://www.googleapis.com/auth/cloud-platform.read-only"


class GCPConnector(Connector):
    source = Source.gcp

    def __init__(self, credentials: dict | None = None, client: Resource | None = None):
        super().__init__(credentials)
        # Allow an injected client (used in tests); otherwise build one from the
        # per-scan credentials. No ambient/global credentials are ever used.
        self._client = client

    # -- client construction -------------------------------------------------
    def _service(self) -> Resource:
        if self._client is not None:
            return self._client
        project_id = self.credentials.get("project_id")
        sa_json = self.credentials.get("service_account_json")
        if not project_id or not sa_json:
            raise ConnectorError("GCP credentials require 'project_id' and 'service_account_json'")
        try:
            import google_auth_httplib2
            import httplib2
            from google.auth.exceptions import GoogleAuthError
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_info(
                sa_json, scopes=[_READ_ONLY_SCOPE]
            )
            # httplib2's default timeout is None (can hang forever). Bound it and
            # wrap with an AuthorizedHttp so the discovery client honors it.
            http = httplib2.Http(timeout=_HTTP_TIMEOUT)
            authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
            return build("iam", "v1", http=authed_http, cache_discovery=False)
        except (ValueError, KeyError, GoogleAuthError) as e:  # malformed key / auth error
            raise ConnectorError(f"invalid GCP service-account key: {e}") from e

    def _project_path(self) -> str:
        project_id = self.credentials.get("project_id")
        if not project_id:
            raise ConnectorError("GCP 'project_id' is required")
        return f"projects/{project_id}"

    # -- contract ------------------------------------------------------------
    def validate_credentials(self) -> bool:
        service = self._service()
        try:
            service.projects().serviceAccounts().list(
                name=self._project_path(), pageSize=1
            ).execute()
            return True
        except HttpError as e:
            raise ConnectorError(f"GCP credentials rejected: {e}") from e

    def discover(self) -> list[AgentRecord]:
        service = self._service()
        project_path = self._project_path()
        try:
            role_map = self._role_map(service, project_path)
            accounts, truncated = self._list_service_accounts(service, project_path)
            records = [self._normalize(service, sa, role_map) for sa in accounts]
        except HttpError as e:
            raise ConnectorError(f"GCP read failed: {e}") from e
        if truncated:
            records.append(_page_cap_note(len(accounts)))
        return records

    # -- reads ---------------------------------------------------------------
    def _list_service_accounts(
        self, service: Resource, project_path: str
    ) -> tuple[list[dict], bool]:
        accounts: list[dict] = []
        page_token: str | None = None
        pages = 0
        truncated = False
        while True:
            resp = (
                service.projects()
                .serviceAccounts()
                .list(name=project_path, pageSize=_PAGE_SIZE, pageToken=page_token)
                .execute()
            )
            accounts.extend(resp.get("accounts", []))
            pages += 1
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
            if pages >= _MAX_PAGES:
                # Never silently truncate — surface the cap as a coverage note.
                truncated = True
                break
        return accounts, truncated

    def _list_keys(self, service: Resource, sa_name: str) -> list[dict]:
        resp = service.projects().serviceAccounts().keys().list(name=sa_name).execute()
        return resp.get("keys", [])

    def _role_map(self, service: Resource, project_path: str) -> dict[str, list[str]]:
        """Map each service-account email to the project roles bound to it."""
        policy = service.projects().getIamPolicy(resource=project_path, body={}).execute()
        mapping: dict[str, list[str]] = {}
        for binding in policy.get("bindings", []):
            role = binding.get("role")
            if not role:
                continue
            for member in binding.get("members", []):
                if member.startswith("serviceAccount:"):
                    email = member.split(":", 1)[1]
                    mapping.setdefault(email, []).append(role)
        return mapping

    # -- normalization -------------------------------------------------------
    def _normalize(
        self, service: Resource, sa: dict, role_map: dict[str, list[str]]
    ) -> AgentRecord:
        email = sa.get("email", "")
        keys = self._list_keys(service, sa.get("name", ""))
        created_at = _earliest_user_key_date(keys)
        owner = _owner_from_sa(sa)
        disabled = bool(sa.get("disabled", False))
        user_key_count = sum(1 for k in keys if k.get("keyType") == "USER_MANAGED")
        return AgentRecord(
            id=f"gcp:serviceaccount:{email}",
            source=Source.gcp,
            type=IdentityType.service_account,
            display_name=sa.get("displayName") or email,
            created_at=created_at,
            # No cheap universal last-used in GCP — see module docstring.
            last_activity_at=None,
            owner=owner,
            # A named owner is unverifiable from IAM alone, so 'unknown', not 'active'.
            owner_status=OwnerStatus.unknown if owner else OwnerStatus.none,
            scopes=role_map.get(email, []),
            raw_metadata={
                "email": email,
                "unique_id": sa.get("uniqueId"),
                "disabled": disabled,
                "user_managed_key_count": user_key_count,
            },
        )


# ---- helpers ---------------------------------------------------------------
def _earliest_user_key_date(keys: list[dict]) -> datetime | None:
    """The SA's own creation isn't in the IAM read surface; the earliest
    user-managed key is our best proxy for how long it has existed."""
    dates: list[datetime] = []
    for key in keys:
        if key.get("keyType") == "USER_MANAGED":
            created = _parse(key.get("validAfterTime"))
            if created:
                dates.append(created)
    return min(dates) if dates else None


def _owner_from_sa(sa: dict) -> str | None:
    description = (sa.get("description") or "").strip()
    if description:
        return description
    labels = sa.get("labels") or {}
    lower = {k.lower(): v for k, v in labels.items()}
    for key in _OWNER_LABEL_KEYS:
        if lower.get(key):
            return lower[key]
    return None


def _page_cap_note(scanned: int) -> AgentRecord:
    return AgentRecord(
        id="gcp:coverage-note:pagination",
        source=Source.gcp,
        type=IdentityType.automation,
        display_name=f"[coverage] stopped after {_MAX_PAGES} pages of serviceAccounts",
        owner_status=OwnerStatus.unknown,
        raw_metadata={"scanned": scanned, "max_pages": _MAX_PAGES, "note": "page cap"},
    )
