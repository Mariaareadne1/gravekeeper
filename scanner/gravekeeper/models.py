"""Core data models for the scanner.

These are the shared vocabulary between connectors (which produce AgentRecords),
the scoring engine (which turns records into Findings), the storage layer, and
the API. Everything is pydantic v2 so validation happens at the boundaries.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Source(str, Enum):
    aws = "aws"
    github = "github"
    gcp = "gcp"
    azure = "azure"
    synthetic = "synthetic"


class IdentityType(str, Enum):
    service_account = "service_account"
    api_key = "api_key"
    oauth_app = "oauth_app"
    automation = "automation"
    agent = "agent"


class OwnerStatus(str, Enum):
    active = "active"  # owner exists and is enabled
    disabled = "disabled"  # owner exists but has been disabled (e.g. offboarded)
    missing = "missing"  # a named owner is recorded but no longer exists
    unknown = "unknown"  # we couldn't determine the owner's status
    none = "none"  # no owner is recorded at all


class ReasonCode(str, Enum):
    NO_ACTIVITY_90D = "NO_ACTIVITY_90D"
    OWNER_DISABLED = "OWNER_DISABLED"
    OWNER_MISSING = "OWNER_MISSING"
    NO_OWNER = "NO_OWNER"
    OVERPRIVILEGED = "OVERPRIVILEGED"
    NEVER_USED_BUT_OLD = "NEVER_USED_BUT_OLD"


class RecommendedAction(str, Enum):
    keep = "keep"
    review = "review"
    retire = "retire"


class AgentRecord(BaseModel):
    """A single non-human identity, normalized across platforms."""

    id: str = Field(..., description="Stable identifier, unique within a scan")
    source: Source
    type: IdentityType
    display_name: str
    created_at: datetime | None = None
    last_activity_at: datetime | None = Field(
        default=None,
        description="Most recent observed use. None means never used or unknown.",
    )
    owner: str | None = None
    owner_status: OwnerStatus = OwnerStatus.unknown
    scopes: list[str] = Field(default_factory=list)
    raw_metadata: dict = Field(default_factory=dict)


class Finding(BaseModel):
    """The scorer's verdict on one AgentRecord."""

    agent_id: str
    is_zombie_candidate: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[ReasonCode] = Field(default_factory=list)
    recommended_action: RecommendedAction = RecommendedAction.keep
    # Human-facing state for the lifecycle registry (Layer 2). Not destructive.
    review_state: str | None = Field(
        default=None, description="null | 'review' | 'keep' set by a human in the UI"
    )


class LifecycleState(str, Enum):
    active = "active"
    under_review = "under_review"
    decommission_requested = "decommission_requested"
    retired = "retired"


class RegistryHistoryEntry(BaseModel):
    """A point-in-time snapshot of a registry entry, captured before an update."""

    changed_at: datetime
    changed_by: str | None = None
    lifecycle_state: LifecycleState
    assigned_owner: str | None = None
    owner_status_override: OwnerStatus | None = None
    note: str | None = None


class RegistryEntry(BaseModel):
    """Human-owned lifecycle/ownership record for one non-human identity.

    Kept separate from Finding so the scan pipeline stays pure — this is joined
    onto findings at the API read boundary only.
    """

    identity_key: str
    source: Source
    identity_id: str
    assigned_owner: str | None = Field(default=None, max_length=256)
    owner_status_override: OwnerStatus | None = None
    lifecycle_state: LifecycleState = LifecycleState.active
    note: str | None = Field(default=None, max_length=2000)
    updated_by: str | None = Field(default=None, max_length=256)
    updated_at: datetime
    history: list[RegistryHistoryEntry] = Field(default_factory=list)


class RegistryUpdate(BaseModel):
    """Partial update to a registry entry. Unset fields are left unchanged."""

    assigned_owner: str | None = Field(default=None, max_length=256)
    owner_status_override: OwnerStatus | None = None
    lifecycle_state: LifecycleState | None = None
    note: str | None = Field(default=None, max_length=2000)
    updated_by: str | None = Field(default=None, max_length=256)
    clear_assigned_owner: bool = False
    clear_note: bool = False
    clear_owner_status_override: bool = False


class ScanResult(BaseModel):
    scan_id: str
    started_at: datetime
    finished_at: datetime | None = None
    environment_label: str
    source: Source
    total_identities: int
    zombie_candidates: int
    findings: list[Finding] = Field(default_factory=list)
    # Records are carried alongside findings so the UI can render context.
    records: list[AgentRecord] = Field(default_factory=list)
