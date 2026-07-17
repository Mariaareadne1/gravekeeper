-- GraveKeeper schema. Run this once in the Supabase SQL editor (or via psql with
-- your database connection string) before switching STORAGE_BACKEND to "supabase".
-- All timestamps are stored as timestamptz. A scan's full result is also kept as
-- a JSONB blob on `scans` so reads are a single row fetch; the normalized
-- `agent_records` and `findings` tables exist for querying across scans later.

create table if not exists scans (
    scan_id text primary key,
    environment_label text not null default '',
    source text not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    total_identities integer not null default 0,
    zombie_candidates integer not null default 0,
    data jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists agent_records (
    scan_id text not null references scans(scan_id) on delete cascade,
    id text not null,
    source text not null,
    type text not null,
    display_name text not null,
    created_at timestamptz,
    last_activity_at timestamptz,
    owner text,
    owner_status text not null default 'unknown',
    scopes jsonb not null default '[]'::jsonb,
    raw_metadata jsonb not null default '{}'::jsonb,
    primary key (scan_id, id)
);

create table if not exists findings (
    scan_id text not null references scans(scan_id) on delete cascade,
    agent_id text not null,
    is_zombie_candidate boolean not null,
    confidence double precision not null,
    reasons jsonb not null default '[]'::jsonb,
    recommended_action text not null default 'keep',
    review_state text,
    primary key (scan_id, agent_id)
);

create index if not exists findings_zombie_idx
    on findings (scan_id, is_zombie_candidate);
