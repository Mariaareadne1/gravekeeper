"""The connector contract.

Every platform GraveKeeper scans implements this interface. A connector's only
job is to *read* its platform's access-control records and normalize them into
`AgentRecord`s — it never mutates anything. Keeping the surface this small is
what lets us add GCP, Azure, Okta, Slack, etc. as small, independent units.

Contract for implementers:
- `validate_credentials()` performs a single cheap read to confirm the supplied
  credentials work and are sufficient. It must not raise on success; it returns
  True/False (and may raise ConnectorError with a helpful message on hard errors).
- `discover()` returns a list of fully-normalized `AgentRecord`s. It must only
  ever call read-only ("list", "get", "describe") APIs of the platform.
- Connectors take their credentials as a plain dict so the API layer can pass
  per-scan, user-supplied credentials without any global/ambient state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import AgentRecord, Source


class ConnectorError(Exception):
    """Raised when a connector cannot complete a read (bad creds, API down)."""


class Connector(ABC):
    #: The platform this connector reads. Set on each subclass.
    source: Source

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Cheaply confirm the credentials work and grant the reads we need."""
        raise NotImplementedError

    @abstractmethod
    def discover(self) -> list[AgentRecord]:
        """Return every non-human identity this connector can see, normalized.

        Implementations MUST use read-only API calls exclusively.
        """
        raise NotImplementedError
