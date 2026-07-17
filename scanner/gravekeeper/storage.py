"""Persistence for scans.

Two interchangeable backends behind one interface:

- `LocalStorage` — a JSON file. Zero setup, always works, used for offline runs,
  the demo, and tests.
- `SupabaseStorage` — Postgres via the Supabase client. Used when configured and
  the migration in migrations/0001_init.sql has been applied.

`get_storage()` picks one based on config. It defaults to local so the app is
runnable on a fresh clone with no external services; set STORAGE_BACKEND=supabase
(and run the migration) to persist to Postgres.
"""

from __future__ import annotations

import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path

from .config import get_settings
from .models import ScanResult


class Storage(ABC):
    @abstractmethod
    def save_scan(self, result: ScanResult) -> None: ...

    @abstractmethod
    def get_scan(self, scan_id: str) -> ScanResult | None: ...

    @abstractmethod
    def list_scans(self) -> list[str]: ...

    def set_review_state(self, scan_id: str, agent_id: str, state: str | None) -> ScanResult | None:
        """Update a finding's human review state (Layer 2). Non-destructive."""
        result = self.get_scan(scan_id)
        if result is None:
            return None
        for f in result.findings:
            if f.agent_id == agent_id:
                f.review_state = state
                break
        else:
            return result
        self.save_scan(result)
        return result


class LocalStorage(Storage):
    """A tiny JSON-file store. Concurrency is guarded with a process lock — fine
    for a single-process dev server and the test suite."""

    def __init__(self, path: str | Path | None = None):
        default = Path(__file__).resolve().parents[1] / "local_scans.json"
        self.path = Path(path) if path else default
        self._lock = threading.Lock()

    def _read_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError:  # pragma: no cover - corrupt file
            return {}

    def _write_all(self, data: dict[str, dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, default=str, indent=2))
        os.replace(tmp, self.path)

    def save_scan(self, result: ScanResult) -> None:
        with self._lock:
            data = self._read_all()
            data[result.scan_id] = json.loads(result.model_dump_json())
            self._write_all(data)

    def get_scan(self, scan_id: str) -> ScanResult | None:
        data = self._read_all()
        raw = data.get(scan_id)
        return ScanResult.model_validate(raw) if raw else None

    def list_scans(self) -> list[str]:
        return list(self._read_all().keys())


class SupabaseStorage(Storage):
    """Persists to Supabase Postgres. Requires the migration to have been run."""

    def __init__(self, url: str, key: str):
        # Imported lazily so the package works without supabase installed/needed.
        from supabase import create_client

        self._client = create_client(url, key)

    def save_scan(self, result: ScanResult) -> None:
        blob = json.loads(result.model_dump_json())
        self._client.table("scans").upsert(
            {
                "scan_id": result.scan_id,
                "environment_label": result.environment_label,
                "source": result.source.value,
                "started_at": result.started_at.isoformat(),
                "finished_at": result.finished_at.isoformat() if result.finished_at else None,
                "total_identities": result.total_identities,
                "zombie_candidates": result.zombie_candidates,
                "data": blob,
            }
        ).execute()

        if result.records:
            self._client.table("agent_records").upsert(
                [
                    {
                        "scan_id": result.scan_id,
                        "id": r.id,
                        "source": r.source.value,
                        "type": r.type.value,
                        "display_name": r.display_name,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "last_activity_at": (
                            r.last_activity_at.isoformat() if r.last_activity_at else None
                        ),
                        "owner": r.owner,
                        "owner_status": r.owner_status.value,
                        "scopes": r.scopes,
                        "raw_metadata": r.raw_metadata,
                    }
                    for r in result.records
                ]
            ).execute()

        if result.findings:
            self._client.table("findings").upsert(
                [
                    {
                        "scan_id": result.scan_id,
                        "agent_id": f.agent_id,
                        "is_zombie_candidate": f.is_zombie_candidate,
                        "confidence": f.confidence,
                        "reasons": [r.value for r in f.reasons],
                        "recommended_action": f.recommended_action.value,
                        "review_state": f.review_state,
                    }
                    for f in result.findings
                ]
            ).execute()

    def get_scan(self, scan_id: str) -> ScanResult | None:
        resp = self._client.table("scans").select("data").eq("scan_id", scan_id).execute()
        rows = resp.data or []
        if not rows:
            return None
        return ScanResult.model_validate(rows[0]["data"])

    def list_scans(self) -> list[str]:
        resp = self._client.table("scans").select("scan_id").execute()
        return [row["scan_id"] for row in (resp.data or [])]


_storage: Storage | None = None


def get_storage() -> Storage:
    """Return the configured storage backend (cached)."""
    global _storage
    if _storage is not None:
        return _storage

    settings = get_settings()
    backend = os.getenv("STORAGE_BACKEND", "auto").lower()

    if backend == "supabase" and settings.supabase_configured:
        _storage = SupabaseStorage(settings.supabase_url, settings.supabase_service_key)
    else:
        # "auto" and everything else default to local — safe on a fresh clone.
        _storage = LocalStorage()
    return _storage


def reset_storage_cache() -> None:
    """Test hook to clear the cached backend."""
    global _storage
    _storage = None
