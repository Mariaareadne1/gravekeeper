"""Storage round-trip tests against the offline LocalStorage backend."""

from __future__ import annotations

from gravekeeper.connectors.synthetic import SyntheticConnector
from gravekeeper.models import LifecycleState, OwnerStatus, RegistryUpdate, Source
from gravekeeper.pipeline import run_scan
from gravekeeper.storage import LocalStorage


def test_local_storage_round_trip(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    connector = SyntheticConnector()
    result = run_scan(connector, now=connector.reference_now)

    store.save_scan(result)
    loaded = store.get_scan(result.scan_id)

    assert loaded is not None
    assert loaded.scan_id == result.scan_id
    assert loaded.total_identities == result.total_identities
    assert loaded.zombie_candidates == result.zombie_candidates
    assert len(loaded.findings) == len(result.findings)
    assert {f.agent_id for f in loaded.findings} == {f.agent_id for f in result.findings}


def test_get_missing_scan_returns_none(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    assert store.get_scan("does-not-exist") is None


def test_list_scans(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    connector = SyntheticConnector()
    r1 = run_scan(connector, now=connector.reference_now, scan_id="scan-1")
    r2 = run_scan(connector, now=connector.reference_now, scan_id="scan-2")
    store.save_scan(r1)
    store.save_scan(r2)
    assert set(store.list_scans()) == {"scan-1", "scan-2"}


def test_set_review_state_is_persisted(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    connector = SyntheticConnector()
    result = run_scan(connector, now=connector.reference_now, scan_id="scan-rev")
    store.save_scan(result)

    target = result.findings[0].agent_id
    store.set_review_state("scan-rev", target, "review")

    loaded = store.get_scan("scan-rev")
    marked = next(f for f in loaded.findings if f.agent_id == target)
    assert marked.review_state == "review"


def test_registry_list_empty_by_default(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    assert store.list_registry_entries() == []


def test_registry_get_missing_returns_none(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    assert store.get_registry_entry("aws:aws:user:jsmith") is None


def test_registry_upsert_creates_entry(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    key = "aws:aws:user:jsmith"

    entry = store.upsert_registry_entry(
        key,
        RegistryUpdate(
            assigned_owner="jsmith",
            lifecycle_state=LifecycleState.under_review,
            updated_by="admin",
        ),
    )

    assert entry.identity_key == key
    assert entry.source is Source.aws
    assert entry.identity_id == "aws:user:jsmith"
    assert entry.assigned_owner == "jsmith"
    assert entry.lifecycle_state is LifecycleState.under_review
    assert entry.history == []
    # Persisted and re-readable.
    loaded = store.get_registry_entry(key)
    assert loaded is not None
    assert loaded.assigned_owner == "jsmith"


def test_registry_upsert_appends_history(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    key = "aws:aws:user:jsmith"

    store.upsert_registry_entry(key, RegistryUpdate(assigned_owner="jsmith", updated_by="admin"))
    updated = store.upsert_registry_entry(
        key,
        RegistryUpdate(
            lifecycle_state=LifecycleState.retired,
            owner_status_override=OwnerStatus.disabled,
            updated_by="ops",
        ),
    )

    assert updated.lifecycle_state is LifecycleState.retired
    assert updated.owner_status_override is OwnerStatus.disabled
    # Owner carried over from the prior write.
    assert updated.assigned_owner == "jsmith"
    # Pre-update snapshot recorded.
    assert len(updated.history) == 1
    snapshot = updated.history[0]
    assert snapshot.lifecycle_state is LifecycleState.active
    assert snapshot.assigned_owner == "jsmith"
    assert snapshot.changed_by == "admin"


def test_registry_upsert_clear_flags(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    key = "aws:aws:user:jsmith"

    store.upsert_registry_entry(key, RegistryUpdate(assigned_owner="jsmith", note="watch this one"))
    cleared = store.upsert_registry_entry(
        key, RegistryUpdate(clear_assigned_owner=True, clear_note=True)
    )

    assert cleared.assigned_owner is None
    assert cleared.note is None


def test_registry_upsert_clear_owner_status_override(tmp_path):
    store = LocalStorage(path=tmp_path / "scans.json")
    key = "aws:aws:user:jsmith"

    store.upsert_registry_entry(key, RegistryUpdate(owner_status_override=OwnerStatus.disabled))
    cleared = store.upsert_registry_entry(key, RegistryUpdate(clear_owner_status_override=True))

    assert cleared.owner_status_override is None


def test_registry_history_is_capped(tmp_path):
    from gravekeeper.storage import _MAX_HISTORY

    store = LocalStorage(path=tmp_path / "scans.json")
    key = "aws:aws:user:jsmith"

    # More updates than the cap; history must not grow without bound.
    for i in range(_MAX_HISTORY + 10):
        store.upsert_registry_entry(key, RegistryUpdate(note=f"update {i}"))

    entry = store.get_registry_entry(key)
    assert entry is not None
    assert len(entry.history) == _MAX_HISTORY
    # The retained window is the most recent snapshots (oldest ones dropped).
    assert entry.history[-1].note == f"update {_MAX_HISTORY + 8}"
