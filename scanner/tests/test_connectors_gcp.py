"""GCP connector tests against an injected fake IAM client (no live project).

The fake implements just the chained googleapiclient surface the connector reads
(`client.projects().serviceAccounts().list(...).execute()`, `.keys().list(...)`,
and `projects().getIamPolicy(...)`) and records every method name it is asked for,
so we can assert the connector only ever makes read-only calls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gravekeeper.connectors.base import ConnectorError
from gravekeeper.connectors.gcp import GCPConnector
from gravekeeper.models import IdentityType, OwnerStatus, Source
from gravekeeper.scoring import score, score_all

PROJECT = "demo-project"
PROJECT_PATH = f"projects/{PROJECT}"


def _sa(email: str, **extra: object) -> dict:
    return {"name": f"{PROJECT_PATH}/serviceAccounts/{email}", "email": email, **extra}


# --- canned data -----------------------------------------------------------
LEGACY = _sa(
    "legacy-bot@demo.iam.gserviceaccount.com",
    displayName="Legacy Batch Bot",
    description="data-team",
    uniqueId="111",
    disabled=False,
)
ORPHAN = _sa("orphan-svc@demo.iam.gserviceaccount.com", uniqueId="222")
DISABLED = _sa(
    "disabled-sa@demo.iam.gserviceaccount.com",
    description="platform-team",
    uniqueId="333",
    disabled=True,
)

KEYS_BY_SA = {
    LEGACY["name"]: {
        "keys": [
            {
                "name": f"{LEGACY['name']}/keys/sysA",
                "keyType": "SYSTEM_MANAGED",
                "validAfterTime": "2026-01-01T00:00:00Z",
            },
            {
                "name": f"{LEGACY['name']}/keys/userA",
                "keyType": "USER_MANAGED",
                "validAfterTime": "2022-01-01T00:00:00Z",
            },
        ]
    },
    DISABLED["name"]: {
        "keys": [
            {
                "name": f"{DISABLED['name']}/keys/userB",
                "keyType": "USER_MANAGED",
                "validAfterTime": "2021-06-01T00:00:00Z",
            }
        ]
    },
}

POLICY = {
    "bindings": [
        {
            "role": "roles/owner",
            "members": [f"serviceAccount:{LEGACY['email']}", "user:human@demo.com"],
        },
        {"role": "roles/viewer", "members": [f"serviceAccount:{ORPHAN['email']}"]},
    ]
}


# --- fake client -----------------------------------------------------------
class _Req:
    def __init__(self, result: dict) -> None:
        self._result = result

    def execute(self) -> dict:
        return self._result


class _Keys:
    def __init__(self, backend: FakeIamClient) -> None:
        self._b = backend

    def list(self, name: str, **_: object) -> _Req:
        self._b.calls.append("projects.serviceAccounts.keys.list")
        return _Req(self._b.keys_by_sa.get(name, {"keys": []}))


class _ServiceAccounts:
    def __init__(self, backend: FakeIamClient) -> None:
        self._b = backend

    def list(self, name: str, pageSize: int | None = None, pageToken: str | None = None) -> _Req:
        self._b.calls.append("projects.serviceAccounts.list")
        return _Req(self._b.sa_pages.get(pageToken, {"accounts": []}))

    def keys(self) -> _Keys:
        return _Keys(self._b)


class _Projects:
    def __init__(self, backend: FakeIamClient) -> None:
        self._b = backend

    def serviceAccounts(self) -> _ServiceAccounts:
        return _ServiceAccounts(self._b)

    def getIamPolicy(self, resource: str, body: dict | None = None) -> _Req:
        self._b.calls.append("projects.getIamPolicy")
        return _Req(self._b.policy)


class FakeIamClient:
    """Minimal stand-in for the googleapiclient IAM service."""

    def __init__(
        self,
        sa_pages: dict[str | None, dict],
        keys_by_sa: dict[str, dict],
        policy: dict,
    ) -> None:
        self.calls: list[str] = []
        self.sa_pages = sa_pages
        self.keys_by_sa = keys_by_sa
        self.policy = policy

    def projects(self) -> _Projects:
        return _Projects(self)


@pytest.fixture
def fake() -> FakeIamClient:
    # Single page containing all three accounts.
    return FakeIamClient(
        sa_pages={None: {"accounts": [LEGACY, ORPHAN, DISABLED]}},
        keys_by_sa=KEYS_BY_SA,
        policy=POLICY,
    )


def _connector(fake: FakeIamClient) -> GCPConnector:
    return GCPConnector(credentials={"project_id": PROJECT}, client=fake)


# --- tests -----------------------------------------------------------------
def test_validate_credentials_happy_path(fake: FakeIamClient) -> None:
    assert _connector(fake).validate_credentials() is True


def test_discover_normalizes_service_accounts(fake: FakeIamClient) -> None:
    records = _connector(fake).discover()
    by_id = {r.id: r for r in records}

    assert len(records) == 3
    assert all(r.source is Source.gcp for r in records)
    assert all(r.type is IdentityType.service_account for r in records)

    legacy = by_id[f"gcp:serviceaccount:{LEGACY['email']}"]
    # created_at comes from the earliest USER_MANAGED key, not the system key.
    assert legacy.created_at == datetime(2022, 1, 1, tzinfo=UTC)
    # roles from the IAM policy become scopes.
    assert legacy.scopes == ["roles/owner"]
    # owner drawn from the SA description; unverifiable so status is 'unknown'.
    assert legacy.owner == "data-team"
    assert legacy.owner_status is OwnerStatus.unknown
    # GCP gives no cheap last-used signal.
    assert legacy.last_activity_at is None
    assert legacy.raw_metadata["user_managed_key_count"] == 1


def test_no_owner_and_no_keys_maps_to_none(fake: FakeIamClient) -> None:
    orphan = next(r for r in _connector(fake).discover() if r.id.endswith(ORPHAN["email"]))
    assert orphan.owner is None
    assert orphan.owner_status is OwnerStatus.none
    assert orphan.created_at is None  # no user-managed key to date it
    assert orphan.scopes == ["roles/viewer"]


def test_disabled_service_account_recorded_in_metadata(fake: FakeIamClient) -> None:
    disabled = next(r for r in _connector(fake).discover() if r.id.endswith(DISABLED["email"]))
    assert disabled.raw_metadata["disabled"] is True


def test_pagination_across_two_pages() -> None:
    page_two_sa = _sa("page2-bot@demo.iam.gserviceaccount.com", uniqueId="444")
    fake = FakeIamClient(
        sa_pages={
            None: {"accounts": [LEGACY], "nextPageToken": "tok2"},
            "tok2": {"accounts": [page_two_sa]},
        },
        keys_by_sa=KEYS_BY_SA,
        policy=POLICY,
    )
    records = _connector(fake).discover()
    ids = {r.id for r in records}
    assert f"gcp:serviceaccount:{LEGACY['email']}" in ids
    assert f"gcp:serviceaccount:{page_two_sa['email']}" in ids
    # two list calls (one per page) confirms the token was followed.
    assert fake.calls.count("projects.serviceAccounts.list") == 2


def test_dormant_owner_role_scores_as_zombie_candidate(fake: FakeIamClient) -> None:
    records = _connector(fake).discover()
    legacy = next(r for r in records if r.id.endswith(LEGACY["email"]))
    # Its user key dates it to 2022 (never used since) -> aged + roles/owner.
    finding = score(legacy)
    assert finding.is_zombie_candidate is True

    # And it surfaces through the batch scorer too.
    findings = {f.agent_id: f for f in score_all(records)}
    assert findings[legacy.id].is_zombie_candidate is True


def test_brand_new_never_used_account_is_not_a_zombie(fake: FakeIamClient) -> None:
    records = _connector(fake).discover()
    legacy = next(r for r in records if r.id.endswith(LEGACY["email"]))
    # A freshly created, never-used account is expected, not dead.
    legacy.created_at = datetime.now(UTC) - timedelta(days=3)
    assert score(legacy).is_zombie_candidate is False


def test_only_read_only_methods_are_invoked(fake: FakeIamClient) -> None:
    from gravekeeper.connectors.gcp import _READ_ONLY_METHODS

    conn = _connector(fake)
    conn.validate_credentials()
    conn.discover()
    assert fake.calls, "expected the connector to make API calls"
    assert all(call in _READ_ONLY_METHODS for call in fake.calls)


def test_empty_project_yields_no_records_without_crashing() -> None:
    # A project with zero service accounts must return an empty list, not raise.
    fake = FakeIamClient(
        sa_pages={None: {"accounts": []}},
        keys_by_sa={},
        policy={"bindings": []},
    )
    records = _connector(fake).discover()
    assert records == []


def test_missing_credentials_raise_connector_error() -> None:
    conn = GCPConnector(credentials={})
    with pytest.raises(ConnectorError):
        conn.validate_credentials()
    with pytest.raises(ConnectorError):
        conn.discover()
