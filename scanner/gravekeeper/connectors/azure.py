"""Read-only Azure / Entra connector — interface skeleton.

This is the connector that directly serves the "govern agents born outside
Microsoft" wedge. The contract is wired so the system treats Azure/Entra as a
first-class source; only the Graph calls need filling in. When implemented it will
read (read-only) via MSAL + Microsoft Graph:

    GET /servicePrincipals            -> app/service principals (non-human identities)
    GET /applications                 -> registered apps and their credentials
    .../servicePrincipals/{id}        -> passwordCredentials / keyCredentials + dates
    GET /auditLogs/signIns            -> last sign-in (last-activity signal)
    GET /users/{ownerId}              -> owner existence/enabled state

Every call is a GET. Owner and owner_status map cleanly from app owners and their
account state (this is where "owner left" is most precisely knowable). Until it's
wired, discover() raises a clear ConnectorError instead of returning empty results.
"""

from __future__ import annotations

from ..models import AgentRecord, Source
from .base import Connector, ConnectorError


class AzureConnector(Connector):
    source = Source.azure

    def validate_credentials(self) -> bool:
        raise ConnectorError(
            "Azure/Entra connector is not implemented yet — the interface is ready. "
            "Use the AWS or GitHub connector, or the demo."
        )

    def discover(self) -> list[AgentRecord]:
        raise ConnectorError("Azure/Entra connector is not implemented yet.")
