"""Storage round-trip tests against the offline LocalStorage backend."""

from __future__ import annotations

from gravekeeper.connectors.synthetic import SyntheticConnector
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
