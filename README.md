# GraveKeeper

GraveKeeper finds the AI agents and automations still running in your accounts that nobody owns anymore.

## The problem

Most companies now run far more non-human identities than human ones — service accounts, API keys, OAuth apps, CI bots, and increasingly autonomous AI agents. Industry estimates put the ratio anywhere from 25:1 to 144:1, with a median around 80 machine identities for every employee. Each one is created in seconds and, unlike a human account, almost never gets cleaned up.

So they pile up. Someone spins up a service account for a one-off migration, or wires an API key into a script, or connects an AI agent to the company inbox — and then the project ends, or that person leaves, and the credential just keeps living. It still has access to email, money, and production systems, but nobody is watching it and nobody remembers why it exists. That's a zombie: alive with real access, but with no owner and no purpose.

Two things make this worse than ordinary tech debt. First, zombies keep *acting* — a forgotten automation runs on stale logic until something breaks (a single dormant function at Knight Capital fired four million orders in 45 minutes and cost around $440M). Second, they're the softest target in the building: an attacker who finds an unwatched credential owns it, because there's no human who'd notice it being abused. And today most orgs genuinely cannot answer the first question you'd ask — *how many agents are running here, and who owns each one?* The data exists, but it's scattered across a dozen consoles that don't talk to each other.

## What it does

GraveKeeper connects to the accounts you point it at, reads their access records (read-only), and builds a single inventory of every non-human identity it finds. Then it scores each one for how likely it is to be abandoned, based on signals like:

- no activity in the audit logs for a long time,
- an owner who no longer exists or has been disabled,
- no documented owner at all,
- broad permissions that are never actually used.

Each candidate comes with a confidence score and the plain-language reasons behind it, so a human can make the call.

Because "who owns this?" is the question the scan can't always answer on its own, GraveKeeper also keeps a **lifecycle registry**: a durable, human-maintained layer where you assign an owner, set a lifecycle state (active, under review, decommission requested, retired), and leave a note on any identity. Those annotations are keyed to the identity and persist across scans, so a decision you make today reappears next to the same agent the next time it turns up — without ever touching the real credential.

## What it does *not* do

- It does not "scan the internet" or track anything outside your accounts. It only reads environments you explicitly connect and grant access to.
- It never creates, modifies, or deletes anything. Every connector uses read-only API calls, and the code is written so it *can't* mutate.
- It does not claim certainty. We can't observe that an identity is dead — we *infer* it from signals and surface it as a candidate for you to confirm.

## Quickstart

You need Python 3.11+ and Node 18+.

**Backend (scanner):**

```bash
cd scanner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn gravekeeper.main:app --reload
```

**Frontend (web):**

```bash
cd web
npm install
npm run dev
```

Then open http://localhost:3000. To see it working with zero setup, click **See a live demo** — the `/demo` page runs a full scan against a built-in sample environment, no login and no credentials required. (The demo and scan pages call the backend, so keep the scanner running on port 8000 while you use them.)

## Testing

The project ships with a full test suite — 106 tests in all, none of which need real cloud credentials.

**Backend** (87 tests, mocks + a synthetic environment with a known answer key):

```bash
cd scanner && source .venv/bin/activate && pytest -q
```

This includes a pipeline test that proves 100% precision and recall on the planted zombies in the synthetic environment.

**Frontend** (14 Vitest + React Testing Library unit/component tests):

```bash
cd web && npm run test:run
```

**End-to-end** (5 Playwright specs covering the demo, scan, and registry flows). These drive a real browser, so the backend must be running on port 8000 first:

```bash
# terminal 1
cd scanner && source .venv/bin/activate && uvicorn gravekeeper.main:app --port 8000
# terminal 2
cd web && npm run e2e
```

## Authentication

The API ships with an **opt-in API-key gate**. With no key configured (the default),
every endpoint is open — local dev and the zero-setup demo stay frictionless. Set
`API_KEY` (see `.env.example`) before exposing the scanner beyond localhost, and the
credential-accepting and write endpoints then require that value in an `X-API-Key`
header:

- **Gated:** real-account scans (`POST /scan` with a non-synthetic connector),
  review writes (`POST /scan/{id}/review`), and registry writes (`PUT /registry`).
- **Still public:** the synthetic demo scan and all reads, so `/demo` keeps working.

The key is compared in constant time. Keep it secret — it is a server-side value, not
an `NEXT_PUBLIC_` one, so a browser deployment should sit behind a proxy (or a Next.js
route handler) that injects the header rather than shipping the key in the bundle.

## Status

Early, and actively being built. The scanner core, scoring engine, synthetic test environment, all four connectors (AWS, GitHub, GCP, and Azure/Entra), and the lifecycle/ownership registry work today. The connectors are proven against mocks and the synthetic environment, not yet against live accounts. More connectors are next.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, boto3 (AWS), httpx (GitHub), Google API client + google-auth (GCP), MSAL + Microsoft Graph (Azure/Entra), pytest + moto for tests
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, with Vitest + React Testing Library for unit/component tests and Playwright for e2e
- **Database:** Supabase (Postgres), with a local offline fallback so the scanner runs without it
