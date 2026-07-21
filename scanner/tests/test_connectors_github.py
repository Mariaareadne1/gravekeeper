"""GitHub connector tests against a mocked REST API (no live token needed).

We use httpx.MockTransport to serve canned responses for the exact GET endpoints
the connector reads, then assert the normalization.
"""

from __future__ import annotations

import httpx
import pytest

from gravekeeper.connectors.github import GitHubConnector
from gravekeeper.models import IdentityType, OwnerStatus, Source

ORG = "northwind"

_ROUTES = {
    "/user": {"login": "northwind-admin"},
    f"/orgs/{ORG}/installations": [
        {
            "id": 101,
            "app_slug": "backup-bot",
            "account": {"login": ORG},
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2026-07-10T00:00:00Z",
            "permissions": {"contents": "read", "metadata": "read"},
            "target_type": "Organization",
        },
        {
            "id": 102,
            "app_slug": "ancient-ci-app",
            "account": {"login": ORG},
            "created_at": "2021-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "permissions": {"administration": "write"},
            "target_type": "Organization",
        },
    ],
    f"/orgs/{ORG}/repos": [
        {"full_name": f"{ORG}/web", "owner": {"login": ORG}},
        {"full_name": f"{ORG}/legacy-infra", "owner": {"login": ORG}},
    ],
    f"/repos/{ORG}/web/keys": [
        {
            "id": 1,
            "title": "prod-deploy",
            "read_only": False,
            "created_at": "2025-06-01T00:00:00Z",
            "last_used": "2026-07-01T00:00:00Z",
            "verified": True,
        }
    ],
    f"/repos/{ORG}/legacy-infra/keys": [
        {
            "id": 2,
            "title": "old-jenkins-key",
            "read_only": False,
            "created_at": "2021-02-01T00:00:00Z",
            "last_used": None,
            "verified": True,
        }
    ],
}


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.url.query:
        # strip query (e.g. ?per_page=100) for routing
        pass
    body = _ROUTES.get(path)
    if body is None:
        return httpx.Response(404, json={"message": "not found"})
    return httpx.Response(200, json=body)


@pytest.fixture
def client():
    transport = httpx.MockTransport(_handler)
    return httpx.Client(transport=transport, base_url="https://api.github.com")


def test_validate_credentials(client):
    conn = GitHubConnector(credentials={"org": ORG}, client=client)
    assert conn.validate_credentials() is True


def test_discovers_installations_and_deploy_keys(client):
    conn = GitHubConnector(credentials={"org": ORG}, client=client)
    records = conn.discover()
    by_id = {r.id: r for r in records}

    installs = [r for r in records if r.type is IdentityType.oauth_app]
    keys = [r for r in records if r.type is IdentityType.api_key]
    assert len(installs) == 2
    assert len(keys) == 2
    assert all(r.source is Source.github for r in records)

    backup = by_id["github:installation:101"]
    assert backup.owner == ORG
    assert "contents" in backup.scopes

    # A deploy key that has never been used carries no last_activity.
    old_key = by_id[f"github:deploykey:{ORG}/legacy-infra:2"]
    assert old_key.last_activity_at is None
    assert old_key.owner == ORG
    assert old_key.owner_status is OwnerStatus.active
    assert old_key.scopes == ["repo:write"]


def test_no_org_skips_installations(client):
    # Without an org, we can't list installations; deploy keys come from /user/repos.
    routes_user = dict(_ROUTES)
    routes_user["/user/repos"] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = routes_user.get(request.url.path)
        return httpx.Response(200 if body is not None else 404, json=body or {})

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    conn = GitHubConnector(credentials={}, client=c)
    records = conn.discover()
    assert records == []


def test_missing_token_raises_without_injected_client():
    from gravekeeper.connectors.base import ConnectorError

    conn = GitHubConnector(credentials={})
    with pytest.raises(ConnectorError):
        conn.validate_credentials()


def test_deploy_key_403_skips_repo_with_note_not_abort(client):
    # A token without repo-admin gets 403 listing one repo's keys. The scan should
    # skip that repo and add a coverage note, NOT abort the whole discover().
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == f"/repos/{ORG}/legacy-infra/keys":
            return httpx.Response(403, json={"message": "Resource not accessible"})
        body = _ROUTES.get(path)
        return httpx.Response(
            200 if body is not None else 404, json=body if body is not None else {}
        )

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    conn = GitHubConnector(credentials={"org": ORG}, client=c)
    records = conn.discover()

    # The accessible repo's key still comes through.
    keys = [r for r in records if r.type is IdentityType.api_key]
    assert any(r.id == f"github:deploykey:{ORG}/web:1" for r in keys)
    # The forbidden repo is skipped, and an honest coverage note is present.
    notes = [r for r in records if "coverage-note" in r.id]
    assert any("Administration: Read" in r.display_name for r in notes)


def test_installations_403_noted_and_deploy_keys_still_scanned(client):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == f"/orgs/{ORG}/installations":
            return httpx.Response(403, json={"message": "forbidden"})
        body = _ROUTES.get(path)
        return httpx.Response(
            200 if body is not None else 404, json=body if body is not None else {}
        )

    c = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    conn = GitHubConnector(credentials={"org": ORG}, client=c)
    records = conn.discover()

    # Installations are noted as skipped, but deploy keys still get scanned.
    assert any("app installations" in r.display_name for r in records)
    assert any(r.type is IdentityType.api_key for r in records)
