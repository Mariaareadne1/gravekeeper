"""Read-only GitHub connector.

Inventories non-human identities reachable with a read-only token: GitHub App
installations, and repository deploy keys (each a standing credential that can act
on a repo). Owners and last-activity are inferred where the API exposes them.

READ-ONLY GUARANTEE
-------------------
Every call is an HTTP GET against the REST API. The connector issues no POST/PATCH/
PUT/DELETE. It only reads:
    GET /user
    GET /user/repos  or  GET /orgs/{org}/repos
    GET /repos/{owner}/{repo}/keys
    GET /orgs/{org}/installations

Credentials (per scan): {"token": "<read-only PAT>", "org": "<optional org>"}.
"""

from __future__ import annotations

import httpx

from ..models import AgentRecord, IdentityType, OwnerStatus, Source
from ._util import parse_iso8601 as _parse
from .base import Connector, ConnectorError

_API = "https://api.github.com"
_MAX_REPOS = 100  # cap deploy-key scanning breadth for a first pass; logged, not silent


class GitHubConnector(Connector):
    source = Source.github

    def __init__(self, credentials: dict | None = None, client: httpx.Client | None = None):
        super().__init__(credentials)
        self._client = client  # injected in tests via a MockTransport

    def _http(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        token = self.credentials.get("token")
        if not token:
            raise ConnectorError("a GitHub token is required")
        return httpx.Client(
            base_url=_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )

    def _get(self, client: httpx.Client, path: str) -> httpx.Response:
        resp = client.get(path)
        if resp.status_code == 401:
            raise ConnectorError("GitHub token rejected (401)")
        if resp.status_code == 403:
            raise ConnectorError("GitHub token lacks required read scope (403)")
        resp.raise_for_status()
        return resp

    def _paginate(self, client: httpx.Client, path: str) -> list[dict]:
        items: list[dict] = []
        next_path: str | None = path
        while next_path:
            resp = self._get(client, next_path)
            page = resp.json()
            if isinstance(page, list):
                items.extend(page)
            next_path = _next_link(resp.headers.get("link"))
        return items

    def validate_credentials(self) -> bool:
        client = self._http()
        try:
            self._get(client, "/user")
            return True
        except httpx.HTTPError as e:
            raise ConnectorError(f"GitHub read failed: {e}") from e

    def discover(self) -> list[AgentRecord]:
        client = self._http()
        org = self.credentials.get("org")
        records: list[AgentRecord] = []
        try:
            records.extend(self._discover_installations(client, org))
            records.extend(self._discover_deploy_keys(client, org))
        except httpx.HTTPError as e:
            raise ConnectorError(f"GitHub read failed: {e}") from e
        return records

    def _discover_installations(self, client: httpx.Client, org: str | None) -> list[AgentRecord]:
        if not org:
            return []
        out: list[AgentRecord] = []
        for inst in self._paginate(client, f"/orgs/{org}/installations"):
            account = (inst.get("account") or {}).get("login")
            app_slug = inst.get("app_slug") or "unknown-app"
            perms = list((inst.get("permissions") or {}).keys())
            out.append(
                AgentRecord(
                    id=f"github:installation:{inst.get('id')}",
                    source=Source.github,
                    type=IdentityType.oauth_app,
                    display_name=f"{app_slug} (app installation)",
                    created_at=_parse(inst.get("created_at")),
                    last_activity_at=_parse(inst.get("updated_at")),
                    owner=account,
                    owner_status=OwnerStatus.unknown if account else OwnerStatus.none,
                    scopes=perms,
                    raw_metadata={"app_slug": app_slug, "target_type": inst.get("target_type")},
                )
            )
        return out

    def _discover_deploy_keys(self, client: httpx.Client, org: str | None) -> list[AgentRecord]:
        repos_path = f"/orgs/{org}/repos" if org else "/user/repos"
        repos = self._paginate(client, f"{repos_path}?per_page=100")
        out: list[AgentRecord] = []
        for repo in repos[:_MAX_REPOS]:
            full = repo.get("full_name")
            owner_login = (repo.get("owner") or {}).get("login")
            for key in self._paginate(client, f"/repos/{full}/keys"):
                read_only = key.get("read_only", True)
                out.append(
                    AgentRecord(
                        id=f"github:deploykey:{full}:{key.get('id')}",
                        source=Source.github,
                        type=IdentityType.api_key,
                        display_name=f"{full} deploy key: {key.get('title')}",
                        created_at=_parse(key.get("created_at")),
                        last_activity_at=_parse(key.get("last_used")),
                        owner=owner_login,
                        owner_status=OwnerStatus.active if owner_login else OwnerStatus.none,
                        scopes=["repo:read"] if read_only else ["repo:write"],
                        raw_metadata={"repo": full, "verified": key.get("verified")},
                    )
                )
        if len(repos) > _MAX_REPOS:
            # Never silently truncate — surface the cap so coverage is honest.
            out.append(_coverage_note(len(repos)))
        return out


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.split(";")
        if len(section) < 2:
            continue
        url = section[0].strip().strip("<>")
        if 'rel="next"' in section[1]:
            # Return a path relative to the base_url.
            return url.replace(_API, "")
    return None


def _coverage_note(total_repos: int) -> AgentRecord:
    return AgentRecord(
        id="github:coverage-note",
        source=Source.github,
        type=IdentityType.automation,
        display_name=f"[coverage] scanned first {_MAX_REPOS} of {total_repos} repos",
        owner_status=OwnerStatus.unknown,
        raw_metadata={"scanned": _MAX_REPOS, "total": total_repos, "note": "deploy-key cap"},
    )
