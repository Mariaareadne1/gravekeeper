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

Then open http://localhost:3000. To see it working with zero setup, click **See a live demo** — the `/demo` page runs a full scan against a built-in sample environment, no login and no credentials required.

To run the tests and see the scoring proven against a synthetic environment with known answers:

```bash
cd scanner && pytest -q
```

## Status

Early, and actively being built. The scanner core, scoring engine, synthetic test environment, all four connectors (AWS, GitHub, GCP, and Azure/Entra), and the lifecycle/ownership registry work today. The connectors are proven against mocks and the synthetic environment, not yet against live accounts. More connectors are next.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, boto3 (AWS), httpx (GitHub), Google API client + google-auth (GCP), MSAL + Microsoft Graph (Azure/Entra), pytest + moto for tests
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, with Vitest + React Testing Library for unit/component tests and Playwright for e2e
- **Database:** Supabase (Postgres), with a local offline fallback so the scanner runs without it
