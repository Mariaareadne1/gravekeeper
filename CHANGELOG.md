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
  (app installations, deploy keys; tested against a mocked REST API). GCP and Azure/Entra
  interfaces are scaffolded and ready to fill in.
- **Storage** with a Supabase (Postgres) backend and a zero-setup local JSON fallback.
- **API** (FastAPI): run a scan, fetch a scan and its findings, mark a finding for
  review/keep, and export findings as JSON or CSV.
- **Results dashboard** with a summary bar, sortable findings table, filters, and a
  detail drawer — plus a no-login `/demo` that runs on the synthetic environment.
- **Read-only connect flow** with a least-privilege IAM policy download.
- **Docs:** README, architecture, threat model, synthetic-environment writeup, and an
  `/about` explainer page.

### Notes

- Everything is read-only by design. No connector makes a mutating API call, and no
  destructive action is implemented — `actions/` is a documented placeholder only.
