# Threat model & trust

The first question anyone sensible asks before connecting an account is: *what can
this thing do to me?* This document answers that directly. The short version: it
reads, and nothing else.

## What we request, and why

GraveKeeper only needs to enumerate identities and their metadata. It never needs
write access to anything.

**AWS.** The exact IAM actions the connector uses (also shipped as a ready-to-attach
least-privilege policy at `web/public/gravekeeper-readonly-policy.json`):

| Action | Why |
| --- | --- |
| `iam:ListUsers`, `iam:ListRoles` | enumerate the identities |
| `iam:ListAccessKeys`, `iam:GetAccessKeyLastUsed` | find keys and when they were last used |
| `iam:ListUserTags` | read an `owner` / `created_by` tag if present |
| `iam:ListAttachedUserPolicies`, `iam:ListUserPolicies` | judge over-privilege |
| `iam:GetRole`, `iam:ListAttachedRolePolicies`, `iam:ListRolePolicies` | role last-used and permissions |

Every one is a `List`/`Get`. There is no `Create`, `Update`, `Put`, `Delete`, or
`Attach` in the set, and the policy grants nothing else.

**GitHub.** A read-only (fine-grained) token with metadata + contents read, and org
read to see app installations. The connector issues only HTTP `GET` requests
(`/user`, `/user/repos` or `/orgs/{org}/repos`, `/repos/{o}/{r}/keys`,
`/orgs/{org}/installations`).

## Read-only guarantee — and how the code proves it

This isn't just a promise in a doc:

- Each connector's module docstring lists the complete set of API calls it makes,
  and they are all reads.
- The AWS connector declares its actions in `_READ_ONLY_ACTIONS`, and a test
  (`test_connector_uses_only_read_actions`) asserts every one starts with
  `List`, `Get`, or `Describe`.
- The least-privilege IAM policy means that even if the code tried to mutate
  something, AWS would refuse it — the credentials literally cannot.

## Data handling

- **Credentials are never persisted.** They're passed in per scan, used to make the
  read calls, and dropped. Only the resulting inventory (which contains no secrets)
  can be saved.
- **Results are stored only if you opt in.** By default the app runs against a local
  file; Supabase persistence is off until you enable it. Either way, a saved scan
  holds identity metadata (names, dates, owners, permission names) — no keys.
- **Deletion.** A stored scan is a single row keyed by `scan_id`; deleting it removes
  its records and findings too (foreign keys cascade).

## Honesty about inference

We cannot observe that an identity is dead. Every "zombie candidate" is an inference
from signals — no recent activity, an owner who left or is missing, no owner at all,
or broad permissions it never exercises. Each finding shows its confidence and the
exact reasons, and a brand-new-but-unused identity is deliberately *not* flagged.
The scoring is plain and inspectable in `scanner/gravekeeper/scoring.py`. A human
confirms; the tool never claims certainty and never acts on its own.

## What GraveKeeper does not do

- It does not scan anything outside the accounts you connect.
- It does not modify, disable, revoke, or delete any identity, key, or policy.
- It does not phone home with your data or share it with third parties.
- It does not require standing access — point it at temporary read-only credentials.
