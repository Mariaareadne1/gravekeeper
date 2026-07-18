"""Read-only Azure / Entra connector.

Inventories the non-human identities in a Microsoft Entra (Azure AD) tenant:
service principals (enterprise apps, app registrations, and managed identities).
For each we resolve creation/credential dates, the most recent sign-in, the owner
and — crucially — whether that owner's account is still enabled, plus the app
roles / delegated permissions it publishes so over-privilege can be judged.

Entra is the source where "the owner left / was disabled" is most precisely
knowable: an owner is a real directory object with an `accountEnabled` flag, so we
can map a disabled owner straight to `OwnerStatus.disabled` rather than guessing.

READ-ONLY GUARANTEE
-------------------
Every call is an HTTP GET against Microsoft Graph. The connector issues no POST/
PATCH/PUT/DELETE. It only reads:
    GET /servicePrincipals                         (paginated non-human identities)
    GET /applications                              (credential start dates)
    GET /servicePrincipals/{id}/owners             (owner + accountEnabled)
    GET /auditLogs/signIns?$filter=appId eq '...'  (last activity; often gated)

Credentials (per scan):
    {"tenant_id": "<dir>", "client_id": "<app>", "client_secret": "<secret>"}

The app registration behind these credentials needs read-only Graph application
permissions (e.g. Application.Read.All, Directory.Read.All, and — for last-activity
— AuditLog.Read.All). Many tenants do not grant AuditLog.Read.All; when the
sign-in endpoint is unavailable we degrade `last_activity_at` to None and surface
an honest coverage note rather than failing the scan.
"""

from __future__ import annotations

from datetime import datetime

import httpx
import msal
import requests

from ..models import AgentRecord, IdentityType, OwnerStatus, Source
from ._util import parse_iso8601 as _parse
from .base import Connector, ConnectorError

_GRAPH = "https://graph.microsoft.com/v1.0"
_AUTHORITY = "https://login.microsoftonline.com"
_SCOPE = "https://graph.microsoft.com/.default"
_MAX_PAGES = 50  # cap paging breadth for a first pass; surfaced, never silent

# Well-known Microsoft Graph app roles broad enough that an abandoned identity
# holding them is a real risk. Normalized to a `resource:*` marker the scorer's
# over-privilege check recognizes, while the raw role value is always kept too.
_BROAD_GRAPH_ROLES = frozenset(
    {
        "Directory.ReadWrite.All",
        "RoleManagement.ReadWrite.Directory",
        "Application.ReadWrite.All",
        "AppRoleAssignment.ReadWrite.All",
    }
)


class AzureConnector(Connector):
    source = Source.azure

    def __init__(
        self,
        credentials: dict | None = None,
        client: httpx.Client | None = None,
        token: str | None = None,
    ):
        super().__init__(credentials)
        self._client = client  # injected in tests via a MockTransport
        self._token = token  # injected in tests so MSAL is never called
        self._signins_available = True  # flipped off if the sign-in log 403s

    # -- auth + transport ---------------------------------------------------
    def _acquire_token(self) -> str:
        if self._token is not None:
            return self._token
        tenant = self.credentials.get("tenant_id")
        client_id = self.credentials.get("client_id")
        secret = self.credentials.get("client_secret")
        if not (tenant and client_id and secret):
            raise ConnectorError(
                "Azure requires tenant_id, client_id, and client_secret credentials"
            )
        # ValueError: bad authority/tenant. RequestException: network failure.
        # The broad fallback ensures any other MSAL internal error still yields a
        # clean ConnectorError (→ 400) rather than a FastAPI 500. None of these
        # exceptions carry the secret — keep it that way in the message.
        try:
            app = msal.ConfidentialClientApplication(
                client_id=client_id,
                authority=f"{_AUTHORITY}/{tenant}",
                client_credential=secret,
            )
            result = app.acquire_token_for_client(scopes=[_SCOPE])
        except (ValueError, requests.exceptions.RequestException) as e:
            raise ConnectorError(f"Azure token acquisition failed: {e}") from e
        except Exception as e:  # pragma: no cover - defensive fallback
            raise ConnectorError(f"Azure token acquisition failed: {e}") from e
        token = result.get("access_token")
        if not token:
            detail = result.get("error_description") or result.get("error") or "unknown error"
            raise ConnectorError(f"Azure token acquisition failed: {detail}")
        return token

    def _http(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        token = self._acquire_token()
        return httpx.Client(
            base_url=_GRAPH,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0,
        )

    def _get(self, client: httpx.Client, url: str) -> httpx.Response:
        resp = client.get(url)
        if resp.status_code == 401:
            raise ConnectorError("Azure token rejected (401)")
        if resp.status_code == 403:
            raise ConnectorError("Azure app lacks required Graph read permission (403)")
        resp.raise_for_status()
        return resp

    def _paginate(
        self, client: httpx.Client, url: str, cap: int = _MAX_PAGES
    ) -> tuple[list[dict], bool]:
        items: list[dict] = []
        next_url: str | None = url
        pages = 0
        truncated = False
        while next_url:
            pages += 1
            resp = self._get(client, next_url)
            data = resp.json()
            items.extend(data.get("value", []))
            next_url = data.get("@odata.nextLink")
            if pages >= cap and next_url:
                truncated = True
                break
        return items, truncated

    # -- contract -----------------------------------------------------------
    def validate_credentials(self) -> bool:
        client = self._http()
        try:
            self._get(client, _url("/servicePrincipals?$top=1"))
            return True
        except httpx.HTTPError as e:
            raise ConnectorError(f"Azure read failed: {e}") from e

    def discover(self) -> list[AgentRecord]:
        client = self._http()
        try:
            principals, truncated = self._paginate(client, _url("/servicePrincipals"))
            credential_dates = self._app_credential_dates(client)
            records = [self._to_record(client, sp, credential_dates) for sp in principals]
        except httpx.HTTPError as e:
            raise ConnectorError(f"Azure read failed: {e}") from e

        if not self._signins_available:
            records.append(_signins_note())
        if truncated:
            records.append(_page_cap_note(len(principals)))
        return records

    # -- enrichment ---------------------------------------------------------
    def _app_credential_dates(self, client: httpx.Client) -> dict[str, datetime]:
        apps, _ = self._paginate(client, _url("/applications"))
        dates: dict[str, datetime] = {}
        for app in apps:
            app_id = app.get("appId")
            starts = [
                parsed
                for cred in app.get("passwordCredentials", []) + app.get("keyCredentials", [])
                if (parsed := _parse(cred.get("startDateTime"))) is not None
            ]
            if app_id and starts:
                dates[app_id] = min(starts)
        return dates

    def _owner(self, client: httpx.Client, sp_id: str) -> tuple[str | None, OwnerStatus]:
        owners, _ = self._paginate(client, _url(f"/servicePrincipals/{sp_id}/owners"))
        if not owners:
            return None, OwnerStatus.none

        def _name(o: dict) -> str | None:
            return o.get("displayName") or o.get("userPrincipalName")

        enabled_owners = [o for o in owners if o.get("accountEnabled") is True]
        if enabled_owners:
            # Any enabled owner means the identity still has a live human behind it.
            return _name(enabled_owners[0]), OwnerStatus.active
        # No owner is enabled. If we positively know at least one is disabled, the
        # identity is offboarded; otherwise the owners' status is indeterminate.
        display = _name(owners[0])
        if any(o.get("accountEnabled") is False for o in owners):
            return display, OwnerStatus.disabled
        return display, OwnerStatus.unknown

    def _last_activity(self, client: httpx.Client, app_id: str | None) -> datetime | None:
        if not app_id or not self._signins_available:
            return None
        url = _url(
            f"/auditLogs/signIns?$filter=appId eq '{app_id}'"
            "&$top=1&$orderby=createdDateTime desc"
        )
        resp = client.get(url)
        # Many tenants gate sign-in logs (no AuditLog.Read.All / no P1 licence).
        # Degrade gracefully instead of failing the whole scan.
        if resp.status_code in (403, 404):
            self._signins_available = False
            return None
        if resp.status_code == 401:
            raise ConnectorError("Azure token rejected (401)")
        resp.raise_for_status()
        values = resp.json().get("value", [])
        if not values:
            return None
        return _parse(values[0].get("createdDateTime"))

    def _to_record(
        self, client: httpx.Client, sp: dict, credential_dates: dict[str, datetime]
    ) -> AgentRecord:
        sp_id = sp.get("id") or ""
        app_id = sp.get("appId")
        owner_name, owner_status = self._owner(client, sp_id)
        created_at = credential_dates.get(app_id) or _parse(sp.get("createdDateTime"))
        return AgentRecord(
            id=f"azure:sp:{sp_id}",
            source=Source.azure,
            type=_identity_type(sp),
            display_name=sp.get("displayName") or sp_id,
            created_at=created_at,
            last_activity_at=self._last_activity(client, app_id),
            owner=owner_name,
            owner_status=owner_status,
            scopes=_scopes_for(sp),
            raw_metadata={
                "app_id": app_id,
                "service_principal_type": sp.get("servicePrincipalType"),
                "account_enabled": sp.get("accountEnabled"),
            },
        )


def _url(path: str) -> str:
    return f"{_GRAPH}{path}"


def _identity_type(sp: dict) -> IdentityType:
    if sp.get("servicePrincipalType") == "ManagedIdentity":
        return IdentityType.service_account
    return IdentityType.oauth_app


def _scopes_for(sp: dict) -> list[str]:
    values: list[str] = []
    for role in sp.get("appRoles", []):
        value = role.get("value")
        if value:
            values.append(value)
    for perm in sp.get("oauth2PermissionScopes", []):
        value = perm.get("value")
        if value:
            values.append(value)
    for value in list(values):
        marker = _broad_marker(value)
        if marker and marker not in values:
            values.append(marker)
    return values


def _broad_marker(value: str) -> str | None:
    if value in _BROAD_GRAPH_ROLES or value.endswith(".ReadWrite.All") or "RoleManagement" in value:
        return f"{value.split('.')[0].lower()}:*"
    return None


def _signins_note() -> AgentRecord:
    return AgentRecord(
        id="azure:coverage-note:signins",
        source=Source.azure,
        type=IdentityType.automation,
        display_name="[coverage] sign-in logs unavailable — last_activity unknown",
        owner_status=OwnerStatus.unknown,
        raw_metadata={
            "note": "auditLogs/signIns returned 403/404",
            "needs": "AuditLog.Read.All (and an Entra ID P1/P2 licence)",
        },
    )


def _page_cap_note(scanned: int) -> AgentRecord:
    return AgentRecord(
        id="azure:coverage-note:page-cap",
        source=Source.azure,
        type=IdentityType.automation,
        display_name=f"[coverage] stopped after {_MAX_PAGES} pages of servicePrincipals",
        owner_status=OwnerStatus.unknown,
        raw_metadata={"scanned": scanned, "max_pages": _MAX_PAGES, "note": "page cap"},
    )
