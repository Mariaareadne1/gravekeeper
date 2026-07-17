"""Run a scan: discover identities with a connector, score them, assemble a
ScanResult. Kept deliberately small and re-runnable so scheduled/continuous
scanning later is a tiny step rather than a rewrite.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .connectors.base import Connector
from .models import ScanResult, Source
from .scoring import Thresholds, score_all


def run_scan(
    connector: Connector,
    environment_label: str = "",
    now: datetime | None = None,
    thresholds: Thresholds | None = None,
    scan_id: str | None = None,
) -> ScanResult:
    started = datetime.now(UTC)
    scan_now = now or started

    records = connector.discover()
    findings = score_all(records, now=scan_now, thresholds=thresholds)
    zombie_count = sum(1 for f in findings if f.is_zombie_candidate)

    return ScanResult(
        scan_id=scan_id or f"scan-{uuid.uuid4().hex[:12]}",
        started_at=started,
        finished_at=datetime.now(UTC),
        environment_label=environment_label or getattr(connector, "environment_label", "scan"),
        source=getattr(connector, "source", Source.synthetic),
        total_identities=len(records),
        zombie_candidates=zombie_count,
        findings=findings,
        records=records,
    )
