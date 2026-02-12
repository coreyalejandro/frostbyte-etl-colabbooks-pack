"""
MinIO per-tenant provisioning per STORAGE_LAYER_PLAN Section 2.
Uses boto3 for bucket creation; mc (MinIO Client) required for IAM.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def _bucket_name(tenant_id: str) -> str:
    """Per plan: tenant-{tenant_id}-bucket, 3-63 chars."""
    name = f"tenant-{tenant_id}-bucket".replace("_", "-").lower()
    if len(name) > 63:
        raise ValueError(f"Bucket name too long: {name}")
    return name


def provision_minio_bucket(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    tenant_id: str,
    secret_key_value: str,
    use_mc_iam: bool = True,
) -> None:
    """
    Create bucket and optionally IAM user/policy via mc.
    When use_mc_iam=False, only creates bucket (dev mode).
    Per STORAGE_LAYER_PLAN 2.1.
    """
    bucket = _bucket_name(tenant_id)
    user = f"tenant-{tenant_id}-access"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise

    if not use_mc_iam:
        return

    # IAM via mc
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            },
        ],
    }
    policy_path = Path(f"/tmp/tenant-{tenant_id}-policy.json")
    try:
        policy_path.write_text(json.dumps(policy))
        # Parse endpoint for mc (strip protocol, use host:port)
        host = endpoint_url.replace("https://", "").replace("http://", "").split("/")[0]
        alias = f"minio-{tenant_id}"
        subprocess.run(
            ["mc", "alias", "set", alias, f"http://{host}", access_key, secret_key],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["mc", "admin", "user", "add", alias, user, secret_key_value],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["mc", "admin", "policy", "create", alias, f"tenant-{tenant_id}-policy", str(policy_path)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["mc", "admin", "policy", "attach", alias, f"tenant-{tenant_id}-policy", f"--user={user}"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "mc (MinIO Client) not found. Install: brew install minio/stable/mc. "
            "Or use use_mc_iam=False for dev mode."
        ) from None
    finally:
        if policy_path.exists():
            policy_path.unlink(missing_ok=True)


def deprovision_minio_bucket(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    tenant_id: str,
) -> None:
    """Remove bucket and IAM user. Per STORAGE_LAYER_PLAN 2.4."""
    bucket = _bucket_name(tenant_id)
    user = f"tenant-{tenant_id}-access"
    alias = f"minio-{tenant_id}"
    host = endpoint_url.replace("https://", "").replace("http://", "").split("/")[0]

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                s3.delete_object(Bucket=bucket, Key=obj["Key"])
        s3.delete_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchBucket":
            raise

    try:
        subprocess.run(["mc", "alias", "set", alias, f"http://{host}", access_key, secret_key], check=True, capture_output=True)
        subprocess.run(["mc", "admin", "user", "remove", alias, user], capture_output=True)
        subprocess.run(["mc", "admin", "policy", "remove", alias, f"tenant-{tenant_id}-policy"], capture_output=True)
    except FileNotFoundError:
        pass
