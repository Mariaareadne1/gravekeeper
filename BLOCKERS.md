# Blockers

Things that need a human with account access. Nothing here stops the app from
running — the scanner, demo, tests, and API all work today on the offline
defaults. These are only needed to turn on the optional Supabase persistence and
to run against real cloud accounts.

## 1. Apply the Supabase migration (to enable Postgres persistence)

The service key can read and write table *rows* over the REST API, but it can't
run DDL (create tables). So the schema has to be applied once by hand:

1. Open the Supabase project → SQL editor.
2. Paste and run `scanner/migrations/0001_init.sql`.
3. In `.env`, set `STORAGE_BACKEND=supabase`.

Until then, storage falls back to a local JSON file (`scanner/local_scans.json`,
gitignored). Everything works either way; this only changes where scans are saved.

## 2. Real cloud credentials for live scans (optional)

The connectors are proven against mocks (AWS via `moto`, GitHub via a mocked REST
transport) and the synthetic environment. To scan real accounts:

- **AWS:** attach the least-privilege read-only policy at
  `web/public/gravekeeper-readonly-policy.json` to an IAM user/role and provide
  temporary read-only keys at scan time.
- **GitHub:** create a read-only fine-grained PAT (metadata + contents read, and
  org read if scanning an org) and provide it at scan time.

No real credentials are needed for development, the demo, or CI.
