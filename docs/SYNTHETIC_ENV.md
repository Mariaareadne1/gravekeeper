# Synthetic environment

The scanner is proven against a synthetic environment with a known answer key.
This is how we can claim "it works" without pointing it at anyone's real accounts,
and it's the regression gate every future change has to pass.

## Where it lives

- `scanner/tests/fixtures/synthetic_env.json` — the environment and the answer key.
- `scanner/gravekeeper/connectors/synthetic.py` — a `SyntheticConnector` that reads
  the fixture and returns normalized `AgentRecord`s, exactly like a real connector.
- `scanner/tests/test_synthetic_pipeline.py` — runs the full scan and checks it
  against the answer key, printing precision and recall.

## What's in it

30 non-human identities across AWS and GitHub, meant to look like a real, messy org:

- **14 that must NOT be flagged:** actively-used, owned service accounts and apps;
  an actively-used admin account (broad scope but not dormant); a legit quarterly
  job last run 100 days ago; a brand-new agent never used yet; a recently-created
  token still in its grace period.
- **16 planted zombies:**
  - 6 whose owner was disabled / left, and which have gone quiet since,
  - 4+ with no activity for 200+ days,
  - 3 admin-scoped identities created long ago and never used once,
  - 2 with no documented owner at all,
  - 1 whose recorded owner no longer exists,
  - with deliberate overlaps (e.g. owner-left *and* over-privileged *and* inactive).

Each identity carries `expected_zombie` and `expected_reasons` — the ground truth.

## Dates

Dates are stored as `created_days_ago` / `last_activity_days_ago` relative to a
fixed `reference_now`. The `SyntheticConnector` converts them to real timestamps
against that reference, and the test scores with `now = reference_now`, so the
result is fully deterministic and never rots as real time passes.

## Running it

```bash
cd scanner
source .venv/bin/activate
pytest tests/test_synthetic_pipeline.py -s
```

Expected output:

```
identities scanned : 30
planted zombies    : 16
caught (TP)        : 16
missed (FN)        : 0
false alarms (FP)  : 0
precision          : 100.00%
recall             : 100.00%
```

If a change to the scoring engine drops recall below 100% or introduces a false
positive, this test fails. That's the point — the planted environment keeps the
scorer honest.

## Testing on real accounts

The synthetic env proves the mechanism. To sanity-check against reality, point the
AWS and GitHub connectors at your own accounts with read-only credentials (see the
connect flow in the app) and eyeball the findings — you should see genuinely
forgotten keys surface. The connectors only ever call list/get/describe APIs.
