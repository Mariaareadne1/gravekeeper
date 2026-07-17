"""Read-only GCP connector — interface skeleton.

The contract is fully wired so the rest of the system already treats GCP as a
first-class source; only the API calls need filling in. When implemented it will
read (read-only) via the Google Cloud IAM / Admin SDK client:

    projects.serviceAccounts.list        -> the service accounts
    projects.serviceAccounts.keys.list   -> their keys and creation dates
    projects.getIamPolicy                -> roles/bindings (for over-privilege)
    logging (activity) or IAM recommender -> last-used signals

Each is a list/get; no mutating call is ever needed. Owner comes from the account
description or a label. Until it's wired, discover() raises a clear ConnectorError
rather than returning misleading empty results.
"""

from __future__ import annotations

from ..models import AgentRecord, Source
from .base import Connector, ConnectorError


class GCPConnector(Connector):
    source = Source.gcp

    def validate_credentials(self) -> bool:
        raise ConnectorError(
            "GCP connector is not implemented yet — the interface is ready. "
            "Use the AWS or GitHub connector, or the demo."
        )

    def discover(self) -> list[AgentRecord]:
        raise ConnectorError("GCP connector is not implemented yet.")
