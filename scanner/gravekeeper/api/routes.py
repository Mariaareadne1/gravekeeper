"""HTTP API for the scanner.

Endpoints:
    GET  /health
    POST /scan                 run a scan (synthetic, or a real connector + creds)
    GET  /scan/{id}            full ScanResult
    GET  /scan/{id}/findings   findings, filterable by ?zombies_only=true
    POST /scan/{id}/review     set a finding's human review state (Layer 2, non-destructive)

Credentials are used for the scan and never persisted — only the resulting
ScanResult (which contains no secrets) is stored.
"""

from __future__ import annotations

import csv
import io
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..connectors.aws import AWSConnector
from ..connectors.azure import AzureConnector
from ..connectors.base import Connector, ConnectorError
from ..connectors.gcp import GCPConnector
from ..connectors.github import GitHubConnector
from ..connectors.synthetic import SyntheticConnector
from ..models import Finding, RegistryEntry, ScanResult
from ..pipeline import run_scan
from ..registry import identity_key_for
from ..storage import get_storage

router = APIRouter()


class ScanRequest(BaseModel):
    connector: Literal["synthetic", "aws", "github", "gcp", "azure"] = "synthetic"
    synthetic: bool = False  # convenience shortcut equivalent to connector="synthetic"
    credentials: dict = Field(default_factory=dict)
    environment_label: str = ""
    persist: bool = True


class ScanSummary(BaseModel):
    scan_id: str
    source: str
    environment_label: str
    total_identities: int
    zombie_candidates: int


class ReviewRequest(BaseModel):
    review_state: str | None = Field(default=None, description="'review', 'keep', or null to clear")


class FindingView(Finding):
    """A Finding joined with its registry entry at read time. Not persisted."""

    registry: RegistryEntry | None = None


def _build_connector(req: ScanRequest) -> Connector:
    name = "synthetic" if req.synthetic else req.connector
    if name == "synthetic":
        return SyntheticConnector()
    if name == "aws":
        return AWSConnector(credentials=req.credentials)
    if name == "github":
        return GitHubConnector(credentials=req.credentials)
    if name == "gcp":
        return GCPConnector(credentials=req.credentials)
    if name == "azure":
        return AzureConnector(credentials=req.credentials)
    raise HTTPException(status_code=400, detail=f"unknown connector: {name}")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/scan", response_model=ScanSummary)
def create_scan(req: ScanRequest) -> ScanSummary:
    connector = _build_connector(req)
    try:
        connector.validate_credentials()
        result = run_scan(connector, environment_label=req.environment_label)
    except ConnectorError as e:
        # Bad/insufficient credentials or an upstream read failure — the caller's
        # problem to fix, not a server error.
        raise HTTPException(status_code=400, detail=str(e)) from e

    if req.persist:
        get_storage().save_scan(result)

    return ScanSummary(
        scan_id=result.scan_id,
        source=result.source.value,
        environment_label=result.environment_label,
        total_identities=result.total_identities,
        zombie_candidates=result.zombie_candidates,
    )


@router.get("/scan/{scan_id}", response_model=ScanResult)
def get_scan(scan_id: str) -> ScanResult:
    result = get_storage().get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return result


@router.get("/scan/{scan_id}/findings", response_model=list[FindingView])
def get_findings(scan_id: str, zombies_only: bool = False) -> list[FindingView]:
    storage = get_storage()
    result = storage.get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")

    findings = result.findings
    if zombies_only:
        findings = [f for f in findings if f.is_zombie_candidate]

    # Join each finding with its registry entry (if any) at the read boundary.
    records_by_id = {r.id: r for r in result.records}
    views: list[FindingView] = []
    for f in findings:
        record = records_by_id.get(f.agent_id)
        entry = None
        if record is not None:
            key = identity_key_for(record.source, f.agent_id)
            entry = storage.get_registry_entry(key)
        views.append(FindingView(**f.model_dump(), registry=entry))
    return views


@router.post("/scan/{scan_id}/review", response_model=Finding)
def set_review(scan_id: str, agent_id: str, req: ReviewRequest) -> Finding:
    if req.review_state not in (None, "review", "keep"):
        raise HTTPException(
            status_code=400, detail="review_state must be 'review', 'keep', or null"
        )
    result = get_storage().set_review_state(scan_id, agent_id, req.review_state)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")
    match = next((f for f in result.findings if f.agent_id == agent_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="finding not found")
    return match


@router.get("/scan/{scan_id}/export")
def export_scan(scan_id: str, format: Literal["json", "csv"] = "json") -> Response:
    result = get_storage().get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")

    if format == "json":
        return Response(
            content=result.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{scan_id}.json"'},
        )

    # CSV: one row per identity, joined with its finding.
    findings = {f.agent_id: f for f in result.findings}
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "source",
            "type",
            "display_name",
            "owner",
            "owner_status",
            "last_activity_at",
            "created_at",
            "scopes",
            "is_zombie_candidate",
            "confidence",
            "reasons",
            "recommended_action",
        ]
    )
    for r in result.records:
        f = findings.get(r.id)
        writer.writerow(
            [
                r.id,
                r.source.value,
                r.type.value,
                r.display_name,
                r.owner or "",
                r.owner_status.value,
                r.last_activity_at.isoformat() if r.last_activity_at else "",
                r.created_at.isoformat() if r.created_at else "",
                " ".join(r.scopes),
                f.is_zombie_candidate if f else "",
                f.confidence if f else "",
                " ".join(rc.value for rc in f.reasons) if f else "",
                f.recommended_action.value if f else "",
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{scan_id}.csv"'},
    )
