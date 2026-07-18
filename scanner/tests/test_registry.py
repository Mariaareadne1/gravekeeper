"""Tests for identity-key round-tripping in the registry helpers."""

from __future__ import annotations

import pytest

from gravekeeper.models import Source
from gravekeeper.registry import identity_key_for, parse_identity_key


def test_identity_key_round_trips_simple():
    key = identity_key_for(Source.aws, "aws:user:jsmith")
    assert key == "aws:aws:user:jsmith"
    source, identity_id = parse_identity_key(key)
    assert source is Source.aws
    assert identity_id == "aws:user:jsmith"


def test_identity_key_round_trips_github_deploy_key():
    # GitHub deploy-key ids contain both '/' and ':' — they must survive the split.
    identity_id = "github:deploykey:owner/repo:123"
    key = identity_key_for(Source.github, identity_id)
    assert key == "github:github:deploykey:owner/repo:123"
    source, parsed_id = parse_identity_key(key)
    assert source is Source.github
    assert parsed_id == identity_id


def test_parse_rejects_malformed_key():
    with pytest.raises(ValueError):
        parse_identity_key("no-colon-here")


def test_parse_rejects_unknown_source():
    with pytest.raises(ValueError):
        parse_identity_key("notasource:some-id")
