"""A connector that reads the synthetic environment fixture.

This lets the entire scan pipeline run with zero external credentials — it powers
the public /demo and the ground-truth pipeline test. Dates in the fixture are
stored relative to a reference "now" (as *_days_ago) so results are deterministic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..models import AgentRecord, IdentityType, OwnerStatus, Source
from .base import Connector, ConnectorError

_DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "synthetic_env.json"
)

# Answer-key fields carried in the fixture but not part of an AgentRecord.
_ANSWER_KEY_FIELDS = {
    "expected_zombie",
    "expected_reasons",
    "note",
    "created_days_ago",
    "last_activity_days_ago",
}


class SyntheticConnector(Connector):
    source = Source.synthetic

    def __init__(self, credentials: dict | None = None, fixture_path: Path | str | None = None):
        super().__init__(credentials)
        self.fixture_path = Path(fixture_path) if fixture_path else _DEFAULT_FIXTURE

    def _load(self) -> dict:
        if not self.fixture_path.exists():
            raise ConnectorError(f"synthetic fixture not found at {self.fixture_path}")
        with self.fixture_path.open() as f:
            return json.load(f)

    @property
    def reference_now(self) -> datetime:
        data = self._load()
        return datetime.fromisoformat(data["reference_now"].replace("Z", "+00:00"))

    @property
    def environment_label(self) -> str:
        return self._load().get("environment_label", "synthetic")

    def validate_credentials(self) -> bool:
        # No credentials needed — just confirm the fixture is readable.
        self._load()
        return True

    def discover(self) -> list[AgentRecord]:
        data = self._load()
        ref = datetime.fromisoformat(data["reference_now"].replace("Z", "+00:00"))
        records: list[AgentRecord] = []
        for item in data["identities"]:
            created = _days_ago_to_dt(ref, item.get("created_days_ago"))
            last = _days_ago_to_dt(ref, item.get("last_activity_days_ago"))
            raw = {k: v for k, v in item.items() if k in _ANSWER_KEY_FIELDS}
            records.append(
                AgentRecord(
                    id=item["id"],
                    source=Source(item["source"]),
                    type=IdentityType(item["type"]),
                    display_name=item["display_name"],
                    created_at=created,
                    last_activity_at=last,
                    owner=item.get("owner"),
                    owner_status=OwnerStatus(item.get("owner_status", "unknown")),
                    scopes=item.get("scopes", []),
                    raw_metadata=raw,
                )
            )
        return records


def _days_ago_to_dt(ref: datetime, days_ago: int | None) -> datetime | None:
    if days_ago is None:
        return None
    return (ref - timedelta(days=days_ago)).astimezone(UTC)
