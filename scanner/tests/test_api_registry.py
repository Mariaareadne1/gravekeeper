"""API tests for the lifecycle/ownership registry endpoints.

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


def test_create_via_put(client):
    key = "aws:aws:user:jsmith"
    resp = client.put(
        "/registry",
        params={"identity_key": key},
        json={"assigned_owner": "jsmith", "lifecycle_state": "under_review", "updated_by": "admin"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["identity_key"] == key
    assert body["source"] == "aws"
    assert body["identity_id"] == "aws:user:jsmith"
    assert body["assigned_owner"] == "jsmith"
    assert body["lifecycle_state"] == "under_review"
    assert body["history"] == []


def test_upsert_appends_history(client):
    key = "github:github:deploykey:owner/repo:123"
    client.put(
        "/registry",
        params={"identity_key": key},
        json={"assigned_owner": "octocat", "updated_by": "admin"},
    )
    resp = client.put(
        "/registry",
        params={"identity_key": key},
        json={"lifecycle_state": "retired", "updated_by": "ops"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["lifecycle_state"] == "retired"
    assert body["identity_id"] == "github:deploykey:owner/repo:123"
    assert len(body["history"]) == 1
    assert body["history"][0]["lifecycle_state"] == "active"
    assert body["history"][0]["assigned_owner"] == "octocat"


def test_put_malformed_identity_key_returns_400(client):
    # No ':' separator → parse_identity_key raises ValueError → 400, not 500.
    resp = client.put(
        "/registry",
        params={"identity_key": "no-colon-here"},
        json={"assigned_owner": "someone"},
    )
    assert resp.status_code == 400


def test_lookup_404_when_missing(client):
    resp = client.get("/registry/lookup", params={"identity_key": "aws:aws:user:ghost"})
    assert resp.status_code == 404


def test_lookup_returns_entry(client):
    key = "aws:aws:user:jsmith"
    client.put("/registry", params={"identity_key": key}, json={"assigned_owner": "jsmith"})
    resp = client.get("/registry/lookup", params={"identity_key": key})
    assert resp.status_code == 200
    assert resp.json()["assigned_owner"] == "jsmith"


def test_list_filtered_by_lifecycle_state(client):
    client.put(
        "/registry",
        params={"identity_key": "aws:aws:user:a"},
        json={"lifecycle_state": "retired"},
    )
    client.put(
        "/registry",
        params={"identity_key": "aws:aws:user:b"},
        json={"lifecycle_state": "active"},
    )

    all_entries = client.get("/registry").json()
    assert len(all_entries) == 2

    retired = client.get("/registry", params={"lifecycle_state": "retired"}).json()
    assert len(retired) == 1
    assert retired[0]["identity_key"] == "aws:aws:user:a"


def test_findings_carry_registry_after_put(client):
    scan_id = client.post("/scan", json={"synthetic": True}).json()["scan_id"]
    scan = client.get(f"/scan/{scan_id}").json()
    record = scan["records"][0]
    agent_id = record["id"]
    key = f"{record['source']}:{agent_id}"

    # Before: registry join is empty for this finding.
    findings = client.get(f"/scan/{scan_id}/findings").json()
    target = next(f for f in findings if f["agent_id"] == agent_id)
    assert target["registry"] is None

    # Register lifecycle/ownership metadata for that identity.
    put = client.put(
        "/registry",
        params={"identity_key": key},
        json={"assigned_owner": "sre-team", "lifecycle_state": "under_review"},
    )
    assert put.status_code == 200

    # After: the finding carries the registry entry.
    findings = client.get(f"/scan/{scan_id}/findings").json()
    target = next(f for f in findings if f["agent_id"] == agent_id)
    assert target["registry"] is not None
    assert target["registry"]["assigned_owner"] == "sre-team"
    assert target["registry"]["lifecycle_state"] == "under_review"
