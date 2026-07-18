"""Identity-key helpers for the lifecycle/ownership registry.

A registry entry is keyed by `identity_key = f"{source.value}:{identity_id}"`.
Connector ids already embed the source prefix (e.g. `aws:user:jsmith`), and
GitHub deploy-key ids contain `/` and `:` (e.g. `github:deploykey:owner/repo:123`),
so the key is split on the FIRST `:` only — everything after it is the id.
"""

from __future__ import annotations

from .models import Source


def identity_key_for(source: Source, identity_id: str) -> str:
    """Build the registry key for a given source and identity id."""
    return f"{source.value}:{identity_id}"


def parse_identity_key(key: str) -> tuple[Source, str]:
    """Split an identity key back into its source and identity id.

    Splits on the FIRST `:` only, so a `:` inside the id survives. Raises
    ValueError on a malformed key or an unknown source.
    """
    source_part, sep, identity_id = key.partition(":")
    if not sep or not identity_id:
        raise ValueError(f"malformed identity_key: {key!r}")
    try:
        source = Source(source_part)
    except ValueError as exc:
        raise ValueError(f"unknown source in identity_key: {key!r}") from exc
    return source, identity_id
