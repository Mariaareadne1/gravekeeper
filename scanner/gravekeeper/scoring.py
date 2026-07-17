"""Zombie confidence scoring.

We cannot observe that an identity is dead. We infer it from signals and return a
confidence score with human-readable reasons. Each signal contributes a weight;
weights sum and saturate to [0, 1]. A record is a zombie *candidate* when the
confidence clears a tunable threshold (default 0.5).

The one false positive we guard against explicitly: a brand-new identity that
simply hasn't been used yet. Recently created + never used is expected, not dead.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from .models import (
    AgentRecord,
    Finding,
    OwnerStatus,
    ReasonCode,
    RecommendedAction,
)

# Scopes broad enough that an abandoned identity holding them is a real risk.
_BROAD_SCOPE_MARKERS = (
    "*",
    "admin",
    "administratoraccess",
    "owner",
    "poweruser",
    "iam:*",
    "root",
)


class Thresholds(BaseModel):
    """Tunable knobs for the scorer. Defaults are sensible; the synthetic test
    pins behavior so changing these can't silently regress recall/precision."""

    inactivity_days: int = 90
    candidate_cutoff: float = 0.5
    retire_cutoff: float = 0.75

    # Signal weights.
    w_no_activity: float = 0.35
    w_never_used_but_old: float = 0.35
    w_owner_disabled: float = 0.40
    w_owner_missing: float = 0.40
    w_no_owner: float = 0.25
    w_overprivileged: float = 0.20


def _is_overprivileged(scopes: list[str]) -> bool:
    for scope in scopes:
        s = scope.strip().lower()
        if s in _BROAD_SCOPE_MARKERS or s.endswith(":*") or s == "*":
            return True
    return False


def _days_between(a: datetime, b: datetime) -> float:
    # Normalize naive datetimes to UTC so subtraction never raises.
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return (a - b).total_seconds() / 86400.0


def score(
    agent: AgentRecord,
    now: datetime | None = None,
    thresholds: Thresholds | None = None,
) -> Finding:
    now = now or datetime.now(timezone.utc)
    t = thresholds or Thresholds()

    reasons: list[ReasonCode] = []
    confidence = 0.0

    age_days = _days_between(now, agent.created_at) if agent.created_at else None
    is_new = age_days is not None and age_days < t.inactivity_days

    # --- Inactivity signals -------------------------------------------------
    inactive = False
    if agent.last_activity_at is not None:
        idle_days = _days_between(now, agent.last_activity_at)
        if idle_days >= t.inactivity_days:
            reasons.append(ReasonCode.NO_ACTIVITY_90D)
            confidence += t.w_no_activity
            inactive = True
    else:
        # Never used. Only a signal if it's had time to be used and isn't brand new.
        if not is_new:
            reasons.append(ReasonCode.NEVER_USED_BUT_OLD)
            confidence += t.w_never_used_but_old
            inactive = True
        # else: brand-new, never-used identity — expected, not a zombie.

    # --- Owner signals ------------------------------------------------------
    if agent.owner_status is OwnerStatus.disabled:
        reasons.append(ReasonCode.OWNER_DISABLED)
        confidence += t.w_owner_disabled
    elif agent.owner_status is OwnerStatus.missing:
        reasons.append(ReasonCode.OWNER_MISSING)
        confidence += t.w_owner_missing
    elif agent.owner is None or agent.owner_status is OwnerStatus.none:
        reasons.append(ReasonCode.NO_OWNER)
        confidence += t.w_no_owner

    # --- Over-privilege -----------------------------------------------------
    # Broad permissions are only a zombie signal when the identity is also
    # dormant — an actively-used admin account is not a zombie.
    if inactive and _is_overprivileged(agent.scopes):
        reasons.append(ReasonCode.OVERPRIVILEGED)
        confidence += t.w_overprivileged

    confidence = max(0.0, min(1.0, confidence))
    is_candidate = confidence >= t.candidate_cutoff

    if confidence >= t.retire_cutoff:
        action = RecommendedAction.retire
    elif is_candidate:
        action = RecommendedAction.review
    else:
        action = RecommendedAction.keep

    return Finding(
        agent_id=agent.id,
        is_zombie_candidate=is_candidate,
        confidence=round(confidence, 3),
        reasons=reasons,
        recommended_action=action,
    )


def score_all(
    agents: list[AgentRecord],
    now: datetime | None = None,
    thresholds: Thresholds | None = None,
) -> list[Finding]:
    now = now or datetime.now(timezone.utc)
    return [score(a, now=now, thresholds=thresholds) for a in agents]
