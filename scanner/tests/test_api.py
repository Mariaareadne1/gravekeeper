"""End-to-end API tests against the synthetic environment.

Uses a LocalStorage pointed at a temp file so the suite never touches real state.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import gravekeeper.storage as storage_mod
from gravekeeper.main import app
from gravekeeper.storage import LocalStorage


@pytest.fixture(autouse=True)
def temp_storage(tmp_path, monkeypatch):
    store = LocalStorage(path=tmp_path / "scans.json")
    monkeypatch.setattr(storage_mod, "_storage", store)
    yield store


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_synthetic_scan_end_to_end(client):
    # Run a scan
    resp = client.post("/scan", json={"synthetic": True})
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total_identities"] == 30
    assert summary["zombie_candidates"] == 16
    scan_id = summary["scan_id"]

    # Fetch full result
    full = client.get(f"/scan/{scan_id}")
    assert full.status_code == 200
    body = full.json()
    assert len(body["findings"]) == 30
    assert len(body["records"]) == 30

    # Findings filtered to zombies only
    zombies = client.get(f"/scan/{scan_id}/findings", params={"zombies_only": True})
    assert zombies.status_code == 200
    zlist = zombies.json()
    assert len(zlist) == 16
    assert all(f["is_zombie_candidate"] for f in zlist)


def test_get_unknown_scan_is_404(client):
    assert client.get("/scan/nope").status_code == 404


def test_review_flow(client):
    scan_id = client.post("/scan", json={"synthetic": True}).json()["scan_id"]
    findings = client.get(f"/scan/{scan_id}/findings").json()
    agent_id = findings[0]["agent_id"]

    resp = client.post(
        f"/scan/{scan_id}/review",
        params={"agent_id": agent_id},
        json={"review_state": "review"},
    )
    assert resp.status_code == 200
    assert resp.json()["review_state"] == "review"

    # Persisted
    reloaded = client.get(f"/scan/{scan_id}").json()
    marked = next(f for f in reloaded["findings"] if f["agent_id"] == agent_id)
    assert marked["review_state"] == "review"


def test_invalid_review_state_rejected(client):
    scan_id = client.post("/scan", json={"synthetic": True}).json()["scan_id"]
    agent_id = client.get(f"/scan/{scan_id}/findings").json()[0]["agent_id"]
    resp = client.post(
        f"/scan/{scan_id}/review",
        params={"agent_id": agent_id},
        json={"review_state": "delete-everything"},
    )
    assert resp.status_code == 400


def test_export_json_and_csv(client):
    scan_id = client.post("/scan", json={"synthetic": True}).json()["scan_id"]

    j = client.get(f"/scan/{scan_id}/export", params={"format": "json"})
    assert j.status_code == 200
    assert j.headers["content-type"].startswith("application/json")
    assert "attachment" in j.headers["content-disposition"]
    assert len(j.json()["findings"]) == 30

    c = client.get(f"/scan/{scan_id}/export", params={"format": "csv"})
    assert c.status_code == 200
    assert c.headers["content-type"].startswith("text/csv")
    lines = c.text.strip().splitlines()
    assert lines[0].startswith("id,source,type")
    assert len(lines) == 31  # header + 30 identities


def test_gcp_and_azure_scans_return_400(client):
    for connector in ("gcp", "azure"):
        resp = client.post("/scan", json={"connector": connector, "credentials": {}})
        assert resp.status_code == 400


def test_aws_scan_with_bad_creds_returns_400(client):
    # No real AWS creds → the connector's validate step should surface a 400,
    # not a 500. (boto3 will fail to authenticate against the real endpoint.)
    resp = client.post(
        "/scan",
        json={
            "connector": "aws",
            "credentials": {"aws_access_key_id": "x", "aws_secret_access_key": "y"},
        },
    )
    assert resp.status_code == 400
