# Changelog

## Unreleased

First working version of GraveKeeper — the read-only scanner that inventories
non-human identities and flags the ones that look abandoned.

### Added

- **Landing page** with the zombie mascot, a mindless-cursor animation, animated
  stat counters, and sections explaining what a zombie agent is, why it costs money,
  how the scan works, and how it stays safe.
- **Scoring engine** that infers zombie candidates from weighted signals (inactivity,
  owner disabled/missing/absent, over-privilege), with a confidence score and
  plain-language reasons. Explicitly avoids flagging brand-new, not-yet-used identities.
- **Synthetic environment** with a ground-truth answer key, and a pipeline test that
  proves 100% precision and recall on the planted zombies.
- **Connectors:** read-only AWS (IAM users, keys, roles; tested with moto) and GitHub
  (app installations, deploy keys; tested against a mocked REST API).
- **GCP connector:** read-only via the Google Cloud IAM API (Google API client +
  google-auth). Lists service accounts, their keys (→ created date), and IAM policy
  roles (→ scopes/over-privilege); owner inferred from the account description/labels.
  GCP exposes no cheap universal "last used" signal, so `last_activity_at` is None and
  aged accounts surface as never-used-but-old candidates; `created_at` is derived from
  the earliest user-managed key. Uses only list/get calls, a 30s client timeout, and
  caps pagination with a coverage note. Tested against a mocked API.
- **Azure/Entra connector:** read-only via MSAL + Microsoft Graph (GET only). Reads
  service principals, application credential dates (→ created), owners and their enabled
  state (→ owner status, including "owner disabled"), sign-in logs (→ last activity),
  and app roles/permissions (→ scopes). Needs read-only Graph app permissions
  (Application.Read.All, Directory.Read.All, AuditLog.Read.All). Sign-in logs also
  require an Entra P1/P2 licence; when unavailable it degrades to no last-activity and
  emits a coverage note rather than failing. Tested against a mocked API.
- **Lifecycle/ownership registry (Layer 2):** a durable, human-annotation layer keyed
  by a stable `identity_key` (`source:identity_id`) that persists across scans and is
  joined back onto findings at read time. Lets a human assign an owner, set a lifecycle
  state (active / under_review / decommission_requested / retired), and add a note;
  every change appends to a bounded history. Strictly non-destructive — annotations
  only; it never touches the real cloud identity. New endpoints: `GET /registry`
  (filterable by lifecycle_state/source), `GET /registry/lookup?identity_key=`, and
  `PUT /registry?identity_key=`. Findings now carry a `registry` field. Ships a Postgres
  migration (`scanner/migrations/0002_registry.sql`) and a local JSON fallback
  (`local_registry.json`), plus a standalone `/registry` page and in-drawer editing on
  the results dashboard.
- **Storage** with a Supabase (Postgres) backend and a zero-setup local JSON fallback.
- **API** (FastAPI): run a scan, fetch a scan and its findings, mark a finding for
  review/keep, and export findings as JSON or CSV.
- **Results dashboard** with a summary bar, sortable findings table, filters, and a
  detail drawer — plus a no-login `/demo` that runs on the synthetic environment.
- **Frontend accessibility hardening:** keyboard-accessible rows and an accessible
  detail drawer (focus trap, Escape to close, focus restore, background inert), plus
  GCP and Azure scan tabs so all four connectors are selectable in the UI. Review-write
  failures now surface visibly instead of being silently swallowed, and there are
  route-level error and not-found boundaries.
- **Read-only connect flow** with a least-privilege IAM policy download.
- **Tests:** the backend grew to 87 passing (new GCP, Azure, and registry suites). The
  frontend went from zero tests to Vitest + React Testing Library unit/component tests
  (14) and Playwright e2e scaffolding (5 specs: demo synthetic scan, connector tabs,
  registry page, landing, docs), runnable with the backend up.
- **Docs:** README, architecture, threat model, synthetic-environment writeup, and an
  `/about` explainer page.

### Notes

- Everything is read-only by design. No connector makes a mutating API call, and no
  destructive action is implemented — `actions/` is a documented placeholder only. The
  lifecycle registry is annotation-only and never touches the real cloud identity.
- `storage_backend` now routes through Settings (was a stray env read); local JSON
  stores are written with owner-only (0600) permissions; the unused PyGithub dependency
  was removed (GitHub uses httpx).
