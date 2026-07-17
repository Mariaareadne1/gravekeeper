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

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..connectors.aws import AWSConnector
from ..connectors.base import Connector, ConnectorError
from ..connectors.github import GitHubConnector
from ..connectors.synthetic import SyntheticConnector
from ..models import Finding, ScanResult
from ..pipeline import run_scan
from ..storage import get_storage

router = APIRouter()


class ScanRequest(BaseModel):
    connector: Literal["synthetic", "aws", "github"] = "synthetic"
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
    review_state: str | None = Field(
        default=None, description="'review', 'keep', or null to clear"
    )


def _build_connector(req: ScanRequest) -> Connector:
    name = "synthetic" if req.synthetic else req.connector
    if name == "synthetic":
        return SyntheticConnector()
    if name == "aws":
        return AWSConnector(credentials=req.credentials)
    if name == "github":
        return GitHubConnector(credentials=req.credentials)
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


@router.get("/scan/{scan_id}/findings", response_model=list[Finding])
def get_findings(scan_id: str, zombies_only: bool = False) -> list[Finding]:
    result = get_storage().get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")
    if zombies_only:
        return [f for f in result.findings if f.is_zombie_candidate]
    return result.findings


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
