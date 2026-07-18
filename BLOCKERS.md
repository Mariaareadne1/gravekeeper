# Blockers

Things that need a human with account access. Nothing here stops the app from
running — the scanner, demo, tests, and API all work today on the offline
defaults. These are only needed to turn on the optional Supabase persistence and
to run against real cloud accounts.

## 1. Apply the Supabase migration (to enable Postgres persistence)

The service key can read and write table *rows* over the REST API, but it can't
run DDL (create tables). So the schema has to be applied once by hand:

1. Open the Supabase project → SQL editor.
2. Paste and run `scanner/migrations/0001_init.sql`, then
   `scanner/migrations/0002_registry.sql` (the lifecycle/ownership registry table).
3. In `.env`, set `STORAGE_BACKEND=supabase`.

Until then, storage falls back to local JSON files (`scanner/local_scans.json` for
scans and `scanner/local_registry.json` for the registry, both gitignored). Everything
works either way; this only changes where scans and annotations are saved.

## 2. Real cloud credentials for live scans (optional)

All four connectors are proven against mocks (AWS via `moto`, GitHub/GCP/Azure via
mocked transports) and the synthetic environment, not yet against live accounts. To
scan real accounts:

- **AWS:** attach the least-privilege read-only policy at
  `web/public/gravekeeper-readonly-policy.json` to an IAM user/role and provide
  temporary read-only keys at scan time.
- **GitHub:** create a read-only fine-grained PAT (metadata + contents read, and
  org read if scanning an org) and provide it at scan time.
- **GCP:** provide `{project_id, service_account_json}` for a service account with
  read-only IAM viewer access.
- **Azure/Entra:** provide `{tenant_id, client_id, client_secret}` for an app
  registration granted read-only Graph permissions (Application.Read.All,
  Directory.Read.All, AuditLog.Read.All). Sign-in-log "last activity" also needs an
  Entra P1/P2 licence; without it that signal is simply absent (a coverage note).

No real credentials are needed for development, the demo, or CI.
