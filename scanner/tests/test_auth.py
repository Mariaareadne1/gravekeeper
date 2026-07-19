"""Tests for the opt-in API-key gate.

Two worlds:
- No key configured (the default): the API is fully open — nothing breaks.
- A key configured: the synthetic demo scan and all reads stay public, but real
  scans and every write require the key in the X-API-Key header.

Auth is toggled by overriding the `get_settings` dependency, which both the /scan
route and the `api_key_guard` dependency resolve.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import gravekeeper.storage as storage_mod
from gravekeeper.config import Settings, get_settings
from gravekeeper.main import app
from gravekeeper.storage import LocalStorage

KEY = "s3cret-api-key"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path, monkeypatch):
    store = LocalStorage(path=tmp_path / "scans.json")
    monkeypatch.setattr(storage_mod, "_storage", store)
    yield store


@pytest.fixture(autouse=True)
def _clear_overrides():
    # Never let an auth override leak into the rest of the suite.
    yield
    app.dependency_overrides.pop(get_settings, None)


def _set_auth(api_key: str) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(api_key=api_key)


@pytest.fixture
def client():
    return TestClient(app)


# --- auth disabled (default) -------------------------------------------------


def test_auth_disabled_by_default_allows_writes(client):
    _set_auth("")  # explicitly no key -> auth off, deterministic regardless of env
    # A registry write goes through with no header.
    resp = client.put(
        "/registry",
        params={"identity_key": "aws:user:jsmith"},
        json={"assigned_owner": "platform-team"},
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_owner"] == "platform-team"


def test_real_scan_without_auth_is_a_credential_error_not_401(client):
    _set_auth("")
    # No key configured: a real connector with bad creds fails on creds (400), not auth.
    resp = client.post("/scan", json={"connector": "aws", "credentials": {"foo": "bar"}})
    assert resp.status_code == 400


# --- auth enabled ------------------------------------------------------------


def test_synthetic_demo_scan_stays_public(client):
    _set_auth(KEY)
    resp = client.post("/scan", json={"synthetic": True})  # no header
    assert resp.status_code == 200
    assert resp.json()["total_identities"] == 30


def test_reads_stay_public_when_auth_enabled(client):
    _set_auth(KEY)
    # Create a (public) synthetic scan, then read it back with no key.
    scan_id = client.post("/scan", json={"synthetic": True}).json()["scan_id"]
    assert client.get(f"/scan/{scan_id}").status_code == 200
    assert client.get(f"/scan/{scan_id}/findings").status_code == 200
    assert client.get("/registry").status_code == 200


def test_real_scan_requires_key(client):
    _set_auth(KEY)
    body = {"connector": "aws", "credentials": {"foo": "bar"}}
    # Missing key -> 401
    assert client.post("/scan", json=body).status_code == 401
    # Wrong key -> 401
    assert client.post("/scan", json=body, headers={"X-API-Key": "nope"}).status_code == 401
    # Correct key -> passes auth, then fails on the bad creds (400, not 401)
    ok = client.post("/scan", json=body, headers={"X-API-Key": KEY})
    assert ok.status_code == 400


def test_registry_write_requires_key(client):
    _set_auth(KEY)
    params = {"identity_key": "aws:user:jsmith"}
    payload = {"assigned_owner": "platform-team"}
    assert client.put("/registry", params=params, json=payload).status_code == 401
    assert (
        client.put(
            "/registry", params=params, json=payload, headers={"X-API-Key": "nope"}
        ).status_code
        == 401
    )
    ok = client.put("/registry", params=params, json=payload, headers={"X-API-Key": KEY})
    assert ok.status_code == 200
    assert ok.json()["assigned_owner"] == "platform-team"


def test_review_write_requires_key(client):
    _set_auth(KEY)
    # The synthetic scan itself is public.
    scan_id = client.post("/scan", json={"synthetic": True}).json()["scan_id"]
    agent_id = client.get(f"/scan/{scan_id}/findings").json()[0]["agent_id"]

    no_key = client.post(
        f"/scan/{scan_id}/review", params={"agent_id": agent_id}, json={"review_state": "review"}
    )
    assert no_key.status_code == 401

    with_key = client.post(
        f"/scan/{scan_id}/review",
        params={"agent_id": agent_id},
        json={"review_state": "review"},
        headers={"X-API-Key": KEY},
    )
    assert with_key.status_code == 200
    assert with_key.json()["review_state"] == "review"
