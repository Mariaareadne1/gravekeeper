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
from datetime import UTC, datetime
from pathlib import Path

from .config import get_settings
from .models import (
    LifecycleState,
    RegistryEntry,
    RegistryHistoryEntry,
    RegistryUpdate,
    ScanResult,
)
from .registry import parse_identity_key

# Keep only the most recent N history snapshots per entry so a hot key can't
# grow the persisted JSON without bound.
_MAX_HISTORY = 50


def _apply_registry_update(
    existing: RegistryEntry | None, identity_key: str, update: RegistryUpdate
) -> RegistryEntry:
    """Produce the next RegistryEntry from an optional existing one and an update.

    Pure and backend-agnostic so both storage backends share the same shape. On
    an update, the pre-update snapshot is appended to `history`; on a first write
    a fresh entry is derived from the identity_key.
    """
    now = datetime.now(UTC)

    if existing is not None:
        history = list(existing.history)
        history.append(
            RegistryHistoryEntry(
                changed_at=existing.updated_at,
                changed_by=existing.updated_by,
                lifecycle_state=existing.lifecycle_state,
                assigned_owner=existing.assigned_owner,
                owner_status_override=existing.owner_status_override,
                note=existing.note,
            )
        )
        source = existing.source
        identity_id = existing.identity_id
        assigned_owner = existing.assigned_owner
        owner_status_override = existing.owner_status_override
        lifecycle_state = existing.lifecycle_state
        note = existing.note
        updated_by = existing.updated_by
    else:
        history = []
        source, identity_id = parse_identity_key(identity_key)
        assigned_owner = None
        owner_status_override = None
        lifecycle_state = LifecycleState.active
        note = None
        updated_by = None

    if update.clear_assigned_owner:
        assigned_owner = None
    elif update.assigned_owner is not None:
        assigned_owner = update.assigned_owner

    if update.clear_note:
        note = None
    elif update.note is not None:
        note = update.note

    if update.clear_owner_status_override:
        owner_status_override = None
    elif update.owner_status_override is not None:
        owner_status_override = update.owner_status_override
    if update.lifecycle_state is not None:
        lifecycle_state = update.lifecycle_state
    if update.updated_by is not None:
        updated_by = update.updated_by

    # Cap history so a hot key can't grow the JSON file without bound.
    history = history[-_MAX_HISTORY:]

    return RegistryEntry(
        identity_key=identity_key,
        source=source,
        identity_id=identity_id,
        assigned_owner=assigned_owner,
        owner_status_override=owner_status_override,
        lifecycle_state=lifecycle_state,
        note=note,
        updated_by=updated_by,
        updated_at=now,
        history=history,
    )


class Storage(ABC):
    @abstractmethod
    def save_scan(self, result: ScanResult) -> None: ...

    @abstractmethod
    def get_scan(self, scan_id: str) -> ScanResult | None: ...

    @abstractmethod
    def list_scans(self) -> list[str]: ...

    @abstractmethod
    def get_registry_entry(self, identity_key: str) -> RegistryEntry | None: ...

    @abstractmethod
    def list_registry_entries(self) -> list[RegistryEntry]: ...

    @abstractmethod
    def upsert_registry_entry(self, identity_key: str, update: RegistryUpdate) -> RegistryEntry: ...

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
        # Registry lives in a sibling file next to the scans store.
        self._registry_path = self.path.with_name("local_registry.json")
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
        # Owner-only perms so the scans file isn't group/world-readable.
        tmp.chmod(0o600)
        os.replace(tmp, self.path)

    def _read_registry(self) -> dict[str, dict]:
        if not self._registry_path.exists():
            return {}
        try:
            return json.loads(self._registry_path.read_text())
        except json.JSONDecodeError:  # pragma: no cover - corrupt file
            return {}

    def _write_registry(self, data: dict[str, dict]) -> None:
        tmp = self._registry_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, default=str, indent=2))
        # Owner-only perms so the registry file isn't group/world-readable.
        tmp.chmod(0o600)
        os.replace(tmp, self._registry_path)

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

    def get_registry_entry(self, identity_key: str) -> RegistryEntry | None:
        raw = self._read_registry().get(identity_key)
        return RegistryEntry.model_validate(raw) if raw else None

    def list_registry_entries(self) -> list[RegistryEntry]:
        return [RegistryEntry.model_validate(raw) for raw in self._read_registry().values()]

    def upsert_registry_entry(self, identity_key: str, update: RegistryUpdate) -> RegistryEntry:
        with self._lock:
            data = self._read_registry()
            existing_raw = data.get(identity_key)
            existing = RegistryEntry.model_validate(existing_raw) if existing_raw else None
            entry = _apply_registry_update(existing, identity_key, update)
            data[identity_key] = json.loads(entry.model_dump_json())
            self._write_registry(data)
        return entry


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

    def get_registry_entry(self, identity_key: str) -> RegistryEntry | None:
        resp = (
            self._client.table("registry_entries")
            .select("*")
            .eq("identity_key", identity_key)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        return RegistryEntry.model_validate(rows[0])

    def list_registry_entries(self) -> list[RegistryEntry]:
        resp = self._client.table("registry_entries").select("*").execute()
        return [RegistryEntry.model_validate(row) for row in (resp.data or [])]

    def upsert_registry_entry(self, identity_key: str, update: RegistryUpdate) -> RegistryEntry:
        # Known limitation: this read-modify-write has no optimistic-concurrency
        # guard, so concurrent updates to the same key can lose a write. Consistent
        # with the rest of the untested Supabase backend; not addressed here.
        existing = self.get_registry_entry(identity_key)
        entry = _apply_registry_update(existing, identity_key, update)
        self._client.table("registry_entries").upsert(
            {
                "identity_key": entry.identity_key,
                "source": entry.source.value,
                "identity_id": entry.identity_id,
                "assigned_owner": entry.assigned_owner,
                "owner_status_override": (
                    entry.owner_status_override.value if entry.owner_status_override else None
                ),
                "lifecycle_state": entry.lifecycle_state.value,
                "note": entry.note,
                "updated_by": entry.updated_by,
                "updated_at": entry.updated_at.isoformat(),
                "history": [json.loads(h.model_dump_json()) for h in entry.history],
            }
        ).execute()
        return entry


_storage: Storage | None = None


def get_storage() -> Storage:
    """Return the configured storage backend (cached)."""
    global _storage
    if _storage is not None:
        return _storage

    settings = get_settings()
    backend = settings.storage_backend.lower()

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
