"""Layer 3 (kill switch) — placeholder ONLY.

This module is intentionally empty. GraveKeeper is read-only: it inventories and
scores, and a human decides what to do. A future, opt-in, explicitly-safe
revocation layer would live here and consume `Finding.recommended_action`.

DESIGN RULE: no destructive action (disable, revoke, delete) is implemented in this
build. If/when it is, it must be gated behind explicit per-action human confirmation,
require its own write-scoped credentials (never the read-only scan credentials), and
be fully reversible or clearly warn when it is not. Nothing here acts on its own.
"""
