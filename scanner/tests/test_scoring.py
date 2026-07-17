from datetime import UTC, datetime, timedelta

from gravekeeper.models import AgentRecord, IdentityType, OwnerStatus, ReasonCode, Source
from gravekeeper.scoring import RecommendedAction, Thresholds, score

NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _rec(**kw):
    base = dict(
        id="x",
        source=Source.aws,
        type=IdentityType.service_account,
        display_name="x",
    )
    base.update(kw)
    return AgentRecord(**base)


def test_healthy_active_agent_is_not_zombie():
    rec = _rec(
        created_at=NOW - timedelta(days=400),
        last_activity_at=NOW - timedelta(days=3),
        owner="platform-team",
        owner_status=OwnerStatus.active,
        scopes=["s3:GetObject"],
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is False
    assert f.confidence < 0.5
    assert f.recommended_action is RecommendedAction.keep
    assert f.reasons == []


def test_clearly_dead_agent_is_high_confidence():
    # Owner left (disabled) + no activity for 200 days + unused admin scope.
    rec = _rec(
        created_at=NOW - timedelta(days=500),
        last_activity_at=NOW - timedelta(days=200),
        owner="former-employee",
        owner_status=OwnerStatus.disabled,
        scopes=["AdministratorAccess"],
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is True
    assert f.confidence >= 0.8
    assert ReasonCode.OWNER_DISABLED in f.reasons
    assert ReasonCode.NO_ACTIVITY_90D in f.reasons
    assert ReasonCode.OVERPRIVILEGED in f.reasons
    assert f.recommended_action is RecommendedAction.retire


def test_dormant_but_owned_is_borderline_not_flagged():
    # A legit quarterly job: owned by an active person, last ran 100 days ago.
    # It trips the inactivity signal but must NOT be flagged on that alone.
    rec = _rec(
        created_at=NOW - timedelta(days=800),
        last_activity_at=NOW - timedelta(days=100),
        owner="data-team",
        owner_status=OwnerStatus.active,
        scopes=["s3:GetObject"],
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is False
    assert 0.0 < f.confidence < 0.5
    assert ReasonCode.NO_ACTIVITY_90D in f.reasons


def test_brand_new_unused_agent_is_not_flagged():
    # Created 3 days ago, never used yet. This is the classic false positive to avoid.
    rec = _rec(
        created_at=NOW - timedelta(days=3),
        last_activity_at=None,
        owner="new-hire",
        owner_status=OwnerStatus.active,
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is False
    assert f.confidence == 0.0
    assert f.reasons == []


def test_no_owner_and_inactive_is_candidate():
    rec = _rec(
        created_at=NOW - timedelta(days=300),
        last_activity_at=NOW - timedelta(days=180),
        owner=None,
        owner_status=OwnerStatus.none,
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is True
    assert ReasonCode.NO_OWNER in f.reasons
    assert ReasonCode.NO_ACTIVITY_90D in f.reasons


def test_never_used_but_old_admin_key_is_candidate():
    # Admin key created almost a year ago and never used once.
    rec = _rec(
        type=IdentityType.api_key,
        created_at=NOW - timedelta(days=320),
        last_activity_at=None,
        owner="ops",
        owner_status=OwnerStatus.active,
        scopes=["*"],
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is True
    assert ReasonCode.NEVER_USED_BUT_OLD in f.reasons
    assert ReasonCode.OVERPRIVILEGED in f.reasons


def test_owner_missing_counts_like_disabled():
    rec = _rec(
        created_at=NOW - timedelta(days=300),
        last_activity_at=NOW - timedelta(days=120),
        owner="ghost-user",
        owner_status=OwnerStatus.missing,
    )
    f = score(rec, now=NOW)
    assert ReasonCode.OWNER_MISSING in f.reasons
    assert f.is_zombie_candidate is True


def test_active_admin_is_not_overprivileged_zombie():
    # Broad scope but used yesterday and owned — must not be flagged.
    rec = _rec(
        created_at=NOW - timedelta(days=200),
        last_activity_at=NOW - timedelta(days=1),
        owner="secops",
        owner_status=OwnerStatus.active,
        scopes=["AdministratorAccess"],
    )
    f = score(rec, now=NOW)
    assert f.is_zombie_candidate is False
    assert ReasonCode.OVERPRIVILEGED not in f.reasons


def test_thresholds_are_tunable():
    rec = _rec(
        created_at=NOW - timedelta(days=300),
        last_activity_at=NOW - timedelta(days=100),
        owner="data-team",
        owner_status=OwnerStatus.active,
    )
    # With a stricter cutoff, the dormant-but-owned job flips to a candidate.
    strict = Thresholds(candidate_cutoff=0.3)
    f = score(rec, now=NOW, thresholds=strict)
    assert f.is_zombie_candidate is True
