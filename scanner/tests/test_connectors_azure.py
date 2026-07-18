"""Azure / Entra connector tests against a mocked Microsoft Graph (no MSAL, no net).

We use httpx.MockTransport to serve canned Graph JSON for the exact GET endpoints
the connector reads, and inject a fake token so `msal` is never constructed. Then
we assert the normalization and that the records drive the scorer correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from gravekeeper.connectors.azure import AzureConnector
from gravekeeper.connectors.base import ConnectorError
from gravekeeper.models import IdentityType, OwnerStatus, Source
from gravekeeper.scoring import ReasonCode, score

_BASE = "https://graph.microsoft.com/v1.0"
_NOW = datetime(2026, 7, 17, tzinfo=UTC)

_SERVICE_PRINCIPALS = [
    {
        "id": "sp-active",
        "appId": "app-active",
        "displayName": "backup-runner",
        "servicePrincipalType": "Application",
        "createdDateTime": "2025-01-01T00:00:00Z",
        "accountEnabled": True,
        "appRoles": [{"value": "User.Read.All"}],
        "oauth2PermissionScopes": [],
    },
    {
        "id": "sp-zombie",
        "appId": "app-zombie",
        "displayName": "legacy-sync",
        "servicePrincipalType": "Application",
        "createdDateTime": "2021-06-01T00:00:00Z",
        "accountEnabled": True,
        "appRoles": [{"value": "Directory.ReadWrite.All"}],
        "oauth2PermissionScopes": [],
    },
]

_APPLICATIONS = [
    {"appId": "app-active", "passwordCredentials": [{"startDateTime": "2025-01-01T00:00:00Z"}]},
    {"appId": "app-zombie", "keyCredentials": [{"startDateTime": "2021-01-01T00:00:00Z"}]},
]

_OWNERS = {
    "sp-active": [{"displayName": "Alice Admin", "accountEnabled": True}],
    "sp-zombie": [{"displayName": "Bob Gone", "accountEnabled": False}],
}

_SIGNINS = {
    "app-active": [{"createdDateTime": "2026-07-01T00:00:00Z"}],
    "app-zombie": [],  # never signed in
}


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    query = request.url.query.decode()

    if path == "/v1.0/servicePrincipals":
        return httpx.Response(200, json={"value": _SERVICE_PRINCIPALS})
    if path == "/v1.0/applications":
        return httpx.Response(200, json={"value": _APPLICATIONS})
    if path.startswith("/v1.0/servicePrincipals/") and path.endswith("/owners"):
        sp_id = path.split("/")[3]
        return httpx.Response(200, json={"value": _OWNERS.get(sp_id, [])})
    if path == "/v1.0/auditLogs/signIns":
        app_id = "app-active" if "app-active" in query else "app-zombie"
        return httpx.Response(200, json={"value": _SIGNINS[app_id]})
    return httpx.Response(404, json={"error": {"message": "not found"}})


def _client(handler=_handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url=_BASE)


def _conn(handler=_handler, **creds) -> AzureConnector:
    # An injected token guarantees MSAL is never called.
    return AzureConnector(credentials=creds, client=_client(handler), token="fake-token")


# -- validate ---------------------------------------------------------------
def test_validate_credentials_happy_path():
    assert _conn().validate_credentials() is True


def test_validate_credentials_raises_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad token"}})

    with pytest.raises(ConnectorError):
        _conn(handler).validate_credentials()


# -- discover / normalization ----------------------------------------------
def test_discover_normalizes_service_principals():
    records = _conn().discover()
    by_id = {r.id: r for r in records}

    assert all(r.source is Source.azure for r in records)
    active = by_id["azure:sp:sp-active"]
    assert active.type is IdentityType.oauth_app
    assert active.display_name == "backup-runner"
    assert "User.Read.All" in active.scopes


def test_credential_dates_become_created_at():
    by_id = {r.id: r for r in _conn().discover()}
    # created_at is the earliest application credential startDateTime, not the SP date.
    assert by_id["azure:sp:sp-active"].created_at == datetime(2025, 1, 1, tzinfo=UTC)
    assert by_id["azure:sp:sp-zombie"].created_at == datetime(2021, 1, 1, tzinfo=UTC)


def test_signins_become_last_activity():
    by_id = {r.id: r for r in _conn().discover()}
    assert by_id["azure:sp:sp-active"].last_activity_at == datetime(2026, 7, 1, tzinfo=UTC)
    # A service principal that has never signed in carries no last_activity.
    assert by_id["azure:sp:sp-zombie"].last_activity_at is None


def test_disabled_owner_maps_to_owner_status_disabled():
    by_id = {r.id: r for r in _conn().discover()}
    zombie = by_id["azure:sp:sp-zombie"]
    assert zombie.owner == "Bob Gone"
    assert zombie.owner_status is OwnerStatus.disabled


def test_dormant_sp_with_disabled_owner_scores_as_high_confidence_zombie():
    by_id = {r.id: r for r in _conn().discover()}
    finding = score(by_id["azure:sp:sp-zombie"], now=_NOW)

    assert finding.is_zombie_candidate is True
    assert finding.confidence >= 0.75  # retire-level confidence
    assert ReasonCode.OWNER_DISABLED in finding.reasons
    assert ReasonCode.NEVER_USED_BUT_OLD in finding.reasons
    # Directory.ReadWrite.All normalizes to a broad marker → over-privilege fires.
    assert ReasonCode.OVERPRIVILEGED in finding.reasons


def test_multiple_owners_with_any_enabled_maps_to_active():
    # Mixed owners: a disabled ex-owner AND a live one. Any enabled owner means
    # the identity still has a human behind it, so status is 'active' and the
    # display owner is the first enabled one.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/owners"):
            return httpx.Response(
                200,
                json={
                    "value": [
                        {"displayName": "Bob Gone", "accountEnabled": False},
                        {"displayName": "Carol Live", "accountEnabled": True},
                    ]
                },
            )
        return _handler(request)

    by_id = {r.id: r for r in _conn(handler).discover()}
    sp = by_id["azure:sp:sp-active"]
    assert sp.owner == "Carol Live"
    assert sp.owner_status is OwnerStatus.active


def test_multiple_owners_all_disabled_maps_to_disabled():
    # No owner is enabled and at least one is positively disabled → offboarded.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/owners"):
            return httpx.Response(
                200,
                json={
                    "value": [
                        {"displayName": "Dave Gone", "accountEnabled": False},
                        {"displayName": "Erin Gone", "accountEnabled": False},
                    ]
                },
            )
        return _handler(request)

    by_id = {r.id: r for r in _conn(handler).discover()}
    sp = by_id["azure:sp:sp-active"]
    assert sp.owner == "Dave Gone"
    assert sp.owner_status is OwnerStatus.disabled


def test_owners_with_indeterminate_status_maps_to_unknown():
    # Owners exist but none report accountEnabled at all → we can't say disabled.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/owners"):
            return httpx.Response(200, json={"value": [{"displayName": "Frank Unknown"}]})
        return _handler(request)

    by_id = {r.id: r for r in _conn(handler).discover()}
    sp = by_id["azure:sp:sp-active"]
    assert sp.owner == "Frank Unknown"
    assert sp.owner_status is OwnerStatus.unknown


def test_no_owner_maps_to_owner_status_none():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/owners"):
            return httpx.Response(200, json={"value": []})
        return _handler(request)

    by_id = {r.id: r for r in _conn(handler).discover()}
    assert by_id["azure:sp:sp-active"].owner is None
    assert by_id["azure:sp:sp-active"].owner_status is OwnerStatus.none


def test_empty_tenant_yields_no_records_without_crashing():
    # A tenant with zero service principals must return cleanly, not raise.
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1.0/servicePrincipals":
            return httpx.Response(200, json={"value": []})
        if path == "/v1.0/applications":
            return httpx.Response(200, json={"value": []})
        if path.endswith("/owners"):
            return httpx.Response(200, json={"value": []})
        if path == "/v1.0/auditLogs/signIns":
            return httpx.Response(200, json={"value": []})
        return httpx.Response(404, json={})

    records = _conn(handler).discover()
    # No real service principals → only (at most) coverage notes, none of them SPs.
    assert all(r.id.startswith("azure:coverage-note") for r in records)
    assert not any(r.id.startswith("azure:sp:") for r in records)


# -- pagination -------------------------------------------------------------
def test_odata_next_link_pagination_across_two_pages():
    page1 = [{"id": "sp-1", "appId": "a1", "displayName": "one", "createdDateTime": None}]
    page2 = [{"id": "sp-2", "appId": "a2", "displayName": "two", "createdDateTime": None}]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        query = request.url.query.decode()
        if path == "/v1.0/servicePrincipals":
            if "page2" in query:
                return httpx.Response(200, json={"value": page2})
            return httpx.Response(
                200,
                json={
                    "value": page1,
                    "@odata.nextLink": f"{_BASE}/servicePrincipals?$skiptoken=page2",
                },
            )
        if path == "/v1.0/applications":
            return httpx.Response(200, json={"value": []})
        if path.endswith("/owners"):
            return httpx.Response(200, json={"value": []})
        if path == "/v1.0/auditLogs/signIns":
            return httpx.Response(200, json={"value": []})
        return httpx.Response(404, json={})

    ids = {r.id for r in _conn(handler).discover()}
    assert ids == {"azure:sp:sp-1", "azure:sp:sp-2"}


# -- failure + degradation --------------------------------------------------
def test_missing_credentials_raises_without_injected_token():
    conn = AzureConnector(credentials={})  # no client, no token
    with pytest.raises(ConnectorError):
        conn.validate_credentials()
    with pytest.raises(ConnectorError):
        conn.discover()


def test_signins_403_degrades_gracefully_with_coverage_note():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1.0/auditLogs/signIns":
            return httpx.Response(403, json={"error": {"message": "AuditLog.Read.All required"}})
        return _handler(request)

    records = _conn(handler).discover()
    by_id = {r.id: r for r in records}
    # Every real SP degrades to unknown last_activity rather than raising.
    assert by_id["azure:sp:sp-active"].last_activity_at is None
    assert by_id["azure:sp:sp-zombie"].last_activity_at is None
    # ...and an honest coverage note is emitted exactly once.
    assert "azure:coverage-note:signins" in by_id
