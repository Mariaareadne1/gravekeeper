"""AWS connector tests against moto (mocked IAM) — no real account needed.

We stand up fake IAM users, keys, and roles with known properties and assert the
connector normalizes them into the AgentRecords we expect.
"""

from __future__ import annotations

from datetime import UTC

import boto3
import pytest
from moto import mock_aws

from gravekeeper.connectors.aws import AWSConnector
from gravekeeper.models import IdentityType, OwnerStatus, Source
from gravekeeper.scoring import score


@pytest.fixture
def iam():
    with mock_aws():
        client = boto3.client("iam", region_name="us-east-1")

        # moto doesn't preload AWS-managed policies, so create customer-managed
        # ones with the same names the connector reports as scopes.
        allow_all = (
            '{"Version":"2012-10-17","Statement":'
            '[{"Effect":"Allow","Action":"*","Resource":"*"}]}'
        )
        admin_arn = client.create_policy(
            PolicyName="AdministratorAccess", PolicyDocument=allow_all
        )["Policy"]["Arn"]
        s3_ro_arn = client.create_policy(
            PolicyName="AmazonS3ReadOnlyAccess", PolicyDocument=allow_all
        )["Policy"]["Arn"]

        # A user owned via tag, with an access key and an admin policy attached.
        client.create_user(UserName="legacy-batch", Tags=[{"Key": "owner", "Value": "jdoe"}])
        client.create_access_key(UserName="legacy-batch")
        client.attach_user_policy(UserName="legacy-batch", PolicyArn=admin_arn)

        # A user with no owner tag and no attached policy.
        client.create_user(UserName="orphan-svc")

        # A role with a policy attached.
        client.create_role(
            RoleName="etl-runner",
            AssumeRolePolicyDocument="{}",
            Tags=[{"Key": "created_by", "Value": "data-team"}],
        )
        client.attach_role_policy(RoleName="etl-runner", PolicyArn=s3_ro_arn)

        yield client


def test_validate_credentials(iam):
    conn = AWSConnector(client=iam)
    assert conn.validate_credentials() is True


def test_discover_returns_users_keys_and_roles(iam):
    conn = AWSConnector(client=iam)
    records = conn.discover()

    by_id = {r.id: r for r in records}
    # two users + one access key + one role
    users = [r for r in records if r.type is IdentityType.service_account]
    keys = [r for r in records if r.type is IdentityType.api_key]
    roles = [r for r in records if r.type is IdentityType.automation]

    assert len(users) == 2
    assert len(keys) == 1
    assert len(roles) == 1
    assert all(r.source is Source.aws for r in records)

    # owner tag is picked up
    legacy = by_id["aws:user:legacy-batch"]
    assert legacy.owner == "jdoe"
    assert "AdministratorAccess" in legacy.scopes

    # no-owner user is marked as such
    orphan = by_id["aws:user:orphan-svc"]
    assert orphan.owner is None
    assert orphan.owner_status is OwnerStatus.none

    # role owner comes from created_by tag
    role = by_id["aws:role:etl-runner"]
    assert role.owner == "data-team"
    assert "AmazonS3ReadOnlyAccess" in role.scopes


def test_access_key_record_belongs_to_user(iam):
    conn = AWSConnector(client=iam)
    records = conn.discover()
    keys = [r for r in records if r.type is IdentityType.api_key]
    assert keys[0].owner == "legacy-batch"
    assert keys[0].owner_status is OwnerStatus.active


def test_discovered_admin_user_scores_as_overprivileged_when_dormant(iam):
    # moto keys/users have no last-used activity, so they read as never-used.
    # Combined with an old-enough creation date this should score as a zombie.
    from datetime import datetime, timedelta

    conn = AWSConnector(client=iam)
    records = conn.discover()
    legacy = next(r for r in records if r.id == "aws:user:legacy-batch")
    # Pretend it was created a year ago so "never used but old" applies.
    legacy.created_at = datetime.now(UTC) - timedelta(days=365)
    f = score(legacy)
    assert f.is_zombie_candidate is True


def test_connector_uses_only_read_actions():
    from gravekeeper.connectors.aws import _READ_ONLY_ACTIONS

    assert all(
        a.split(":")[1].startswith(("List", "Get", "Describe")) for a in _READ_ONLY_ACTIONS
    ), "connector's declared actions must all be read-only"
