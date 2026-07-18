"""Shared helpers for connectors.

Small, dependency-free utilities used across multiple platform connectors so the
same behavior isn't re-implemented (and allowed to drift) in each one.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso8601(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp into a UTC-aware datetime.

    None-safe: returns None for a missing/empty value. A trailing ``Z`` is
    normalized to ``+00:00`` before parsing, and the result is converted to UTC.
    Returns None on an unparseable value rather than raising.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:  # pragma: no cover
        return None
