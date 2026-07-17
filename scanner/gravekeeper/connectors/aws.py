"""Read-only AWS IAM connector.

Inventories the non-human identities in an AWS account: IAM users, their access
keys, and IAM roles. For each we pull creation date, last-used timestamps,
attached policies (to judge over-privilege), and an owner from tags where present.

READ-ONLY GUARANTEE
-------------------
This connector calls ONLY these IAM APIs, all of which are list/get:
    list_users, list_access_keys, get_access_key_last_used, list_user_tags,
    list_attached_user_policies, list_user_policies,
    list_roles, get_role, list_attached_role_policies, list_role_policies
It never calls any create/update/delete/put API. `_READ_ONLY_ACTIONS` documents
the exact allow-list, which mirrors the least-privilege IAM policy we hand users.
"""

from __future__ import annotations

from datetime import UTC, datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from ..models import AgentRecord, IdentityType, OwnerStatus, Source
from .base import Connector, ConnectorError

# The complete set of AWS actions this connector uses. Must stay in sync with the
# least-privilege policy in web/public and docs/THREAT_MODEL.md.
_READ_ONLY_ACTIONS = (
    "iam:ListUsers",
    "iam:ListAccessKeys",
    "iam:GetAccessKeyLastUsed",
    "iam:ListUserTags",
    "iam:ListAttachedUserPolicies",
    "iam:ListUserPolicies",
    "iam:ListRoles",
    "iam:GetRole",
    "iam:ListAttachedRolePolicies",
    "iam:ListRolePolicies",
)

_OWNER_TAG_KEYS = ("owner", "created_by", "createdby", "team")


class AWSConnector(Connector):
    source = Source.aws

    def __init__(self, credentials: dict | None = None, client=None):
        super().__init__(credentials)
        # Allow an injected client (used by moto tests); otherwise build one from
        # the per-scan credentials. No ambient/global credentials are used.
        self._client = client

    def _iam(self):
        if self._client is not None:
            return self._client
        c = self.credentials
        try:
            return boto3.client(
                "iam",
                aws_access_key_id=c.get("aws_access_key_id"),
                aws_secret_access_key=c.get("aws_secret_access_key"),
                aws_session_token=c.get("aws_session_token"),
                region_name=c.get("region_name", "us-east-1"),
            )
        except (BotoCoreError, ValueError) as e:  # pragma: no cover - construction
            raise ConnectorError(f"could not build AWS client: {e}") from e

    def validate_credentials(self) -> bool:
        try:
            self._iam().list_users(MaxItems=1)
            return True
        except ClientError as e:
            raise ConnectorError(f"AWS credentials rejected: {e}") from e
        except BotoCoreError as e:
            raise ConnectorError(f"AWS read failed: {e}") from e

    def discover(self) -> list[AgentRecord]:
        iam = self._iam()
        records: list[AgentRecord] = []
        try:
            records.extend(self._discover_users_and_keys(iam))
            records.extend(self._discover_roles(iam))
        except ClientError as e:
            raise ConnectorError(f"AWS read failed: {e}") from e
        return records

    # -- users + access keys -------------------------------------------------
    def _discover_users_and_keys(self, iam) -> list[AgentRecord]:
        out: list[AgentRecord] = []
        for user in _paginate(iam, "list_users", "Users"):
            username = user["UserName"]
            tags = _tags_for_user(iam, username)
            owner = _owner_from_tags(tags)
            scopes = _user_scopes(iam, username)

            key_dates: list[datetime] = []
            for key in _paginate(iam, "list_access_keys", "AccessKeyMetadata", UserName=username):
                last_used = _access_key_last_used(iam, key["AccessKeyId"])
                if last_used:
                    key_dates.append(last_used)
                out.append(
                    AgentRecord(
                        id=f"aws:key:{key['AccessKeyId']}",
                        source=Source.aws,
                        type=IdentityType.api_key,
                        display_name=f"{username} access key",
                        created_at=_as_utc(key.get("CreateDate")),
                        last_activity_at=last_used,
                        owner=username,
                        # The key's owner is the IAM user, which exists here.
                        owner_status=OwnerStatus.active,
                        scopes=scopes,
                        raw_metadata={
                            "access_key_id": key["AccessKeyId"],
                            "status": key.get("Status"),
                        },
                    )
                )

            # last activity for the user = most recent of password/key use
            user_last = user.get("PasswordLastUsed")
            candidates = [d for d in ([_as_utc(user_last)] + key_dates) if d]
            user_activity = max(candidates) if candidates else None

            out.append(
                AgentRecord(
                    id=f"aws:user:{username}",
                    source=Source.aws,
                    type=IdentityType.service_account,
                    display_name=username,
                    created_at=_as_utc(user.get("CreateDate")),
                    last_activity_at=user_activity,
                    owner=owner,
                    owner_status=OwnerStatus.unknown if owner else OwnerStatus.none,
                    scopes=scopes,
                    raw_metadata={"arn": user.get("Arn"), "tags": tags},
                )
            )
        return out

    # -- roles ---------------------------------------------------------------
    def _discover_roles(self, iam) -> list[AgentRecord]:
        out: list[AgentRecord] = []
        for role in _paginate(iam, "list_roles", "Roles"):
            name = role["RoleName"]
            # get_role returns richer RoleLastUsed than list_roles.
            detail = iam.get_role(RoleName=name)["Role"]
            last_used = _as_utc((detail.get("RoleLastUsed") or {}).get("LastUsedDate"))
            tags = {t["Key"]: t["Value"] for t in detail.get("Tags", [])}
            owner = _owner_from_tags(tags)
            scopes = _role_scopes(iam, name)
            out.append(
                AgentRecord(
                    id=f"aws:role:{name}",
                    source=Source.aws,
                    type=IdentityType.automation,
                    display_name=name,
                    created_at=_as_utc(detail.get("CreateDate")),
                    last_activity_at=last_used,
                    owner=owner,
                    owner_status=OwnerStatus.unknown if owner else OwnerStatus.none,
                    scopes=scopes,
                    raw_metadata={"arn": detail.get("Arn"), "tags": tags},
                )
            )
        return out


# ---- helpers ---------------------------------------------------------------
def _paginate(iam, method: str, key: str, **kwargs):
    """Yield items across pages, whether or not the method has a paginator."""
    if iam.can_paginate(method):
        for page in iam.get_paginator(method).paginate(**kwargs):
            yield from page.get(key, [])
    else:  # pragma: no cover - fallback
        yield from getattr(iam, method)(**kwargs).get(key, [])


def _tags_for_user(iam, username: str) -> dict[str, str]:
    try:
        tags = iam.list_user_tags(UserName=username).get("Tags", [])
        return {t["Key"]: t["Value"] for t in tags}
    except ClientError:  # pragma: no cover - permissions
        return {}


def _owner_from_tags(tags: dict[str, str]) -> str | None:
    lower = {k.lower(): v for k, v in tags.items()}
    for k in _OWNER_TAG_KEYS:
        if lower.get(k):
            return lower[k]
    return None


def _user_scopes(iam, username: str) -> list[str]:
    scopes: list[str] = []
    for p in _paginate(iam, "list_attached_user_policies", "AttachedPolicies", UserName=username):
        scopes.append(p["PolicyName"])
    for name in _paginate(iam, "list_user_policies", "PolicyNames", UserName=username):
        scopes.append(name)
    return scopes


def _role_scopes(iam, name: str) -> list[str]:
    scopes: list[str] = []
    for p in _paginate(iam, "list_attached_role_policies", "AttachedPolicies", RoleName=name):
        scopes.append(p["PolicyName"])
    for pn in _paginate(iam, "list_role_policies", "PolicyNames", RoleName=name):
        scopes.append(pn)
    return scopes


def _access_key_last_used(iam, key_id: str) -> datetime | None:
    try:
        info = iam.get_access_key_last_used(AccessKeyId=key_id)
        return _as_utc(info.get("AccessKeyLastUsed", {}).get("LastUsedDate"))
    except ClientError:  # pragma: no cover
        return None


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
