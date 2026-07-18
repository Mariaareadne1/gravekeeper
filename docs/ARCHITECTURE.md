# Architecture

GraveKeeper is a monorepo with two apps: a Python scanner (`/scanner`) and a
Next.js web app (`/web`). The scanner does the work; the web app is the face and
the dashboard.

```
connectors ──> AgentRecord[] ──> scoring ──> Finding[] ──> ScanResult ──> storage
   (read)         (normalized)     (infer)     (verdict)     (bundle)      (persist)
                                                                 │
                                                          FastAPI  ──>  Next.js UI
```

## The scanner (`/scanner/gravekeeper`)

- **`models.py`** — the shared vocabulary (`AgentRecord`, `Finding`, `ScanResult`)
  as Pydantic v2 models. Every layer speaks these.
- **`connectors/`** — one module per platform, all implementing the `Connector`
  ABC in `base.py` (`validate_credentials()` + `discover() -> list[AgentRecord]`).
  A connector's only job is to *read* its platform and normalize the results. It
  never mutates anything. Adding a platform is adding one file — this is the moat.
  - `synthetic.py` — reads the ground-truth fixture; powers the demo and tests.
  - `aws.py` — read-only IAM (users, keys, roles) via boto3.
  - `github.py` — read-only REST (app installations, deploy keys) via httpx.
  - `gcp.py` — read-only Google Cloud IAM API (service accounts, keys, IAM policy
    roles) via the Google API client + google-auth. GCP has no cheap universal
    "last used" signal, so `last_activity_at` is None and `created_at` is derived
    from the earliest user-managed key; list/get calls only, 30s timeout, capped
    pagination with a coverage note.
  - `azure.py` — read-only Microsoft Graph (GET only) via MSAL (service principals,
    credential dates, owners + enabled state, sign-in logs, app roles). Sign-in logs
    need AuditLog.Read.All plus an Entra P1/P2 licence; without them it degrades to
    no last-activity and emits a coverage note rather than failing.
- **`scoring.py`** — pure, offline-testable inference. Weighted signals (inactivity,
  owner disabled/missing/absent, over-privilege) combine into a confidence score
  and human-readable reasons. Deliberately guards against the brand-new-but-unused
  false positive. Tunable via `Thresholds`.
- **`pipeline.py`** — `run_scan(connector) -> ScanResult`: discover, score, bundle.
  Small and re-runnable so scheduled/continuous scanning is a later add, not a
  rewrite.
- **`storage.py`** — a `Storage` interface with two backends: `LocalStorage` (JSON
  file, zero-setup default) and `SupabaseStorage` (Postgres). Identical interface,
  so swapping is trivial.
- **`api/routes.py` + `main.py`** — FastAPI: `POST /scan`, `GET /scan/{id}`,
  `GET /scan/{id}/findings`, `POST /scan/{id}/review`, `GET /scan/{id}/export`,
  `GET /registry`, `GET /registry/lookup?identity_key=`, `PUT /registry?identity_key=`,
  `GET /health`, with CORS for the web origin. The registry is joined onto findings at
  this read boundary — the scan pipeline itself stays pure.
- **`actions/`** — a deliberately empty placeholder for a future safe-revocation
  layer (Layer 3). No destructive action is implemented in this build, by design.

## The web app (`/web`)

- **App Router** pages: `/` (landing), `/demo` (no-login synthetic scan), `/scan`
  (read-only connect flow, with AWS/GitHub/GCP/Azure tabs), `/registry` (the lifecycle
  annotation view), `/docs/threat-model`, `/about`. Rows and the detail drawer are
  keyboard-accessible (focus trap, Escape, focus restore, background inert), and
  route-level error and not-found boundaries are in place.
- **`lib/api.ts` / `lib/types.ts`** — the typed client and models mirroring the
  backend. `NEXT_PUBLIC_API_BASE_URL` points it at the scanner.
- **`components/`** — the design system pieces: the zombie mascot and mindless-cursor
  SVGs, animated stat counters, and the shared `ResultsDashboard` used by both
  `/demo` and `/scan`.

## Data flow for a scan

1. The UI calls `POST /scan` with a connector name and (for real scans) read-only
   credentials, or `{ "synthetic": true }`.
2. The API builds the connector, calls `run_scan`, and persists the `ScanResult`.
   Credentials are used for the read calls and never stored.
3. The UI fetches `GET /scan/{id}` and renders the dashboard. Each finding is joined
   with any matching lifecycle-registry annotation (by `identity_key`) at this read
   boundary, so the persisted scan stays exactly as scored. Marking a finding for
   review/keep calls `POST /scan/{id}/review`, and owner/lifecycle edits call
   `PUT /registry` — both are notes only, never a destructive act.

## How it scales

- **More connectors → more coverage.** The `Connector` contract keeps each platform
  independent; AWS, GitHub, GCP, and Azure/Entra ship today, and Okta, Slack, etc. slot
  in without touching the core.
- **Lifecycle registry (Layer 2).** Shipped: a durable annotation layer keyed by a
  stable `identity_key` (`source:identity_id`) that persists across scans and is joined
  onto findings at the API read boundary, so the scan pipeline stays pure. A human can
  assign an owner, set a lifecycle state (active / under_review / decommission_requested
  / retired), and add a note; every change appends to a bounded history. It is strictly
  annotation-only — it never touches the real cloud identity. Stored in both backends
  (Postgres via `0002_registry.sql`, or a local `local_registry.json` fallback) and
  exposed through the `GET`/`PUT /registry` endpoints and the `/registry` page.
- **Kill switch (Layer 3).** `recommended_action` is shaped so a future, explicitly
  safe revocation layer can consume it. Nothing destructive ships here.
- **Continuous scanning.** A scan is a pure, re-runnable function, so scheduling is
  a small step.
