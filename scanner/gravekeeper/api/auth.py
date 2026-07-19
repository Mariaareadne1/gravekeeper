"""API-key authentication for the write / credential-accepting endpoints.

The gate is deliberately opt-in. When no `API_KEY` is configured, `auth_enabled`
is False and every check is a no-op — local dev, the test suite, and the
zero-setup demo all keep working unchanged. Once a key is set (before exposing
the API beyond localhost), the protected endpoints require it in the `X-API-Key`
header, compared in constant time.

Two entrypoints:
- `enforce_api_key(...)` — a plain function for endpoints that are only
  *conditionally* protected (the /scan route lets the synthetic demo through).
- `api_key_guard` — a FastAPI dependency for always-protected (write) endpoints.
"""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from ..config import Settings, get_settings

_UNAUTHORIZED_DETAIL = "Missing or invalid API key. Send it in the X-API-Key header."


def enforce_api_key(x_api_key: str | None, settings: Settings) -> None:
    """Raise 401 unless auth is disabled or the supplied key matches.

    Uses `hmac.compare_digest` so the comparison time doesn't leak the key.
    """
    if not settings.auth_enabled:
        return  # no key configured -> the API is open
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_UNAUTHORIZED_DETAIL,
        )


def api_key_guard(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """FastAPI dependency guarding always-protected (write) endpoints."""
    enforce_api_key(x_api_key, settings)
