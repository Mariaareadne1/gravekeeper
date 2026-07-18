from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from gravekeeper.models import (
    AgentRecord,
    Finding,
    IdentityType,
    LifecycleState,
    OwnerStatus,
    ReasonCode,
    RecommendedAction,
    RegistryEntry,
    RegistryHistoryEntry,
    ScanResult,
    Source,
)


def test_agent_record_minimal_valid():
    rec = AgentRecord(
        id="svc-1",
        source=Source.aws,
        type=IdentityType.service_account,
        display_name="billing-reconciler",
    )
    assert rec.owner is None
    assert rec.owner_status is OwnerStatus.unknown
    assert rec.scopes == []
    assert rec.last_activity_at is None


def test_agent_record_full_valid():
    rec = AgentRecord(
        id="key-9",
        source=Source.aws,
        type=IdentityType.api_key,
        display_name="legacy-metrics-key",
        created_at=datetime(2022, 1, 1, tzinfo=UTC),
        last_activity_at=datetime(2023, 1, 1, tzinfo=UTC),
        owner="jdoe",
        owner_status=OwnerStatus.disabled,
        scopes=["s3:*", "iam:List*"],
        raw_metadata={"arn": "arn:aws:iam::123:user/x"},
    )
    assert rec.owner_status is OwnerStatus.disabled
    assert "s3:*" in rec.scopes


def test_agent_record_rejects_bad_enum():
    with pytest.raises(ValidationError):
        AgentRecord(
            id="x",
            source="not-a-real-source",  # type: ignore[arg-type]
            type=IdentityType.agent,
            display_name="x",
        )


def test_finding_confidence_bounds():
    with pytest.raises(ValidationError):
        Finding(agent_id="a", is_zombie_candidate=True, confidence=1.5)
    with pytest.raises(ValidationError):
        Finding(agent_id="a", is_zombie_candidate=False, confidence=-0.1)


def test_finding_valid():
    f = Finding(
        agent_id="svc-1",
        is_zombie_candidate=True,
        confidence=0.9,
        reasons=[ReasonCode.NO_ACTIVITY_90D, ReasonCode.OWNER_DISABLED],
        recommended_action=RecommendedAction.retire,
    )
    assert f.recommended_action is RecommendedAction.retire
    assert ReasonCode.OWNER_DISABLED in f.reasons


def test_scan_result_round_trips_through_json():
    result = ScanResult(
        scan_id="scan-abc",
        started_at=datetime(2026, 7, 16, tzinfo=UTC),
        environment_label="unit-test",
        source=Source.synthetic,
        total_identities=1,
        zombie_candidates=1,
        findings=[Finding(agent_id="svc-1", is_zombie_candidate=True, confidence=0.8)],
        records=[
            AgentRecord(
                id="svc-1",
                source=Source.synthetic,
                type=IdentityType.agent,
                display_name="ghost",
            )
        ],
    )
    dumped = result.model_dump_json()
    restored = ScanResult.model_validate_json(dumped)
    assert restored.scan_id == "scan-abc"
    assert restored.findings[0].confidence == 0.8
    assert restored.records[0].display_name == "ghost"


def test_registry_entry_round_trips_json():
    entry = RegistryEntry(
        identity_key="aws:user:jsmith",
        source=Source.aws,
        identity_id="aws:user:jsmith",
        assigned_owner="jsmith",
        owner_status_override=OwnerStatus.disabled,
        lifecycle_state=LifecycleState.under_review,
        note="pending offboarding",
        updated_by="admin",
        updated_at=datetime(2026, 7, 17, tzinfo=UTC),
        history=[
            RegistryHistoryEntry(
                changed_at=datetime(2026, 7, 16, tzinfo=UTC),
                changed_by="admin",
                lifecycle_state=LifecycleState.active,
            )
        ],
    )
    dumped = entry.model_dump_json()
    restored = RegistryEntry.model_validate_json(dumped)
    assert restored.identity_key == "aws:user:jsmith"
    assert restored.lifecycle_state is LifecycleState.under_review
    assert restored.owner_status_override is OwnerStatus.disabled
    assert len(restored.history) == 1
    assert restored.history[0].lifecycle_state is LifecycleState.active


def test_registry_entry_defaults():
    entry = RegistryEntry(
        identity_key="github:deploykey:owner/repo:123",
        source=Source.github,
        identity_id="github:deploykey:owner/repo:123",
        updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )
    assert entry.assigned_owner is None
    assert entry.owner_status_override is None
    assert entry.lifecycle_state is LifecycleState.active
    assert entry.note is None
    assert entry.updated_by is None
    assert entry.history == []
