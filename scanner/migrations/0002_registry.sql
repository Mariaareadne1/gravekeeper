-- GraveKeeper lifecycle/ownership registry (Layer 2). Run this after 0001_init.sql
-- when using STORAGE_BACKEND=supabase. Registry entries are human-owned records
-- joined onto findings at the API read boundary; they never mutate scan data.

create table if not exists registry_entries (
    identity_key text primary key,
    source text not null,
    identity_id text not null,
    assigned_owner text,
    owner_status_override text,
    lifecycle_state text not null default 'active',
    note text,
    updated_by text,
    updated_at timestamptz not null default now(),
    history jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists registry_entries_source_idx on registry_entries (source);
create index if not exists registry_entries_lifecycle_idx on registry_entries (lifecycle_state);
