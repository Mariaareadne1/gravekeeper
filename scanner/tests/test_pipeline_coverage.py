"""A coverage note is a connector's honest 'I couldn't read X' marker — never a
real identity. The pipeline must keep it out of scoring, out of the identity
count, and out of the findings/records, surfacing it only as a coverage note.
"""

from __future__ import annotations

from datetime import UTC, datetime

from gravekeeper.connectors.base import Connector
from gravekeeper.models import AgentRecord, IdentityType, OwnerStatus, Source
from gravekeeper.pipeline import run_scan


class _FakeConnector(Connector):
    source = Source.github

    def validate_credentials(self) -> bool:
        return True

    def discover(self) -> list[AgentRecord]:
        real = AgentRecord(
            id="github:deploykey:acme/api:1",
            source=Source.github,
            type=IdentityType.api_key,
            display_name="acme/api deploy key: old-ci",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
            last_activity_at=None,  # never used + old -> a genuine candidate
            owner=None,
            owner_status=OwnerStatus.none,
            scopes=["repo:write"],
        )
        note = AgentRecord(
            id="github:coverage-note:forbidden",
            source=Source.github,
            type=IdentityType.coverage_note,
            display_name="[coverage] skipped deploy keys on 25 repo(s) — token needs admin",
            owner_status=OwnerStatus.unknown,
        )
        return [real, note]


def test_coverage_note_is_not_scored_or_counted():
    result = run_scan(_FakeConnector(), now=datetime(2026, 7, 21, tzinfo=UTC))

    # Only the real identity is counted and scored.
    assert result.total_identities == 1
    assert len(result.findings) == 1
    assert len(result.records) == 1
    assert result.findings[0].agent_id == "github:deploykey:acme/api:1"

    # The note never appears as a finding or a record...
    assert all("coverage-note" not in f.agent_id for f in result.findings)
    assert all(r.type is not IdentityType.coverage_note for r in result.records)

    # ...it is surfaced only as a coverage note.
    assert result.coverage_notes == [
        "[coverage] skipped deploy keys on 25 repo(s) — token needs admin"
    ]

    # And the genuine dormant key is still detected — the fix doesn't hide real zombies.
    assert result.zombie_candidates == 1
