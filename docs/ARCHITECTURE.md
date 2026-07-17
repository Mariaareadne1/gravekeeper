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
  - `gcp.py`, `azure.py` — stubs implementing the interface, ready to fill in.
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
  `GET /health`, with CORS for the web origin.
- **`actions/`** — a deliberately empty placeholder for a future safe-revocation
  layer (Layer 3). No destructive action is implemented in this build, by design.

## The web app (`/web`)

- **App Router** pages: `/` (landing), `/demo` (no-login synthetic scan), `/scan`
  (read-only connect flow), `/docs/threat-model`, `/about`.
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
3. The UI fetches `GET /scan/{id}` and renders the dashboard. Marking a finding for
   review/keep calls `POST /scan/{id}/review` — a note only, never a destructive act.

## How it scales

- **More connectors → more coverage.** The `Connector` contract keeps each platform
  independent; GCP, Azure, Okta, Slack, etc. slot in without touching the core.
- **Lifecycle registry (Layer 2).** `Finding.review_state` seeds owner assignment
  and review dates.
- **Kill switch (Layer 3).** `recommended_action` is shaped so a future, explicitly
  safe revocation layer can consume it. Nothing destructive ships here.
- **Continuous scanning.** A scan is a pure, re-runnable function, so scheduling is
  a small step.
