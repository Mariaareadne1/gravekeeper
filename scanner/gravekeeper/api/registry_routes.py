"""HTTP API for the lifecycle/ownership registry (Layer 2).

Endpoints:
    GET  /registry                     list entries, filter by ?lifecycle_state=&?source=
    GET  /registry/lookup?identity_key= one entry (404 if missing)
    PUT  /registry?identity_key=        create-or-update an entry (RegistryUpdate body)

GitHub deploy-key ids contain `/`, so the identity_key is always passed as a
query param, never a path segment.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import LifecycleState, RegistryEntry, RegistryUpdate, Source
from ..storage import get_storage

router = APIRouter()


@router.get("/registry", response_model=list[RegistryEntry])
def list_registry(
    lifecycle_state: LifecycleState | None = None,
    source: Source | None = None,
) -> list[RegistryEntry]:
    entries = get_storage().list_registry_entries()
    if lifecycle_state is not None:
        entries = [e for e in entries if e.lifecycle_state is lifecycle_state]
    if source is not None:
        entries = [e for e in entries if e.source is source]
    return entries


@router.get("/registry/lookup", response_model=RegistryEntry)
def lookup_registry(identity_key: str) -> RegistryEntry:
    entry = get_storage().get_registry_entry(identity_key)
    if entry is None:
        raise HTTPException(status_code=404, detail="registry entry not found")
    return entry


@router.put("/registry", response_model=RegistryEntry)
def upsert_registry(identity_key: str, update: RegistryUpdate) -> RegistryEntry:
    try:
        return get_storage().upsert_registry_entry(identity_key, update)
    except ValueError as e:
        # Malformed identity_key or unknown source on a first write.
        raise HTTPException(status_code=400, detail=str(e)) from e
