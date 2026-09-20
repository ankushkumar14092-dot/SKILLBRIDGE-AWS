import os
import re
import boto3
from functools import lru_cache

MODE = os.getenv("MODE", "build").lower()
BUCKET = os.getenv("S3_BUCKET", "skillbridge-resumes")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")

_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{1,255}$")


def _sanitize_id(value: str) -> str:
    if not _ID_RE.match(value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def _sanitize_filename(value: str) -> str:
    if not _FILENAME_RE.match(value):
        raise ValueError(f"Invalid filename: {value!r}")
    return value


@lru_cache(maxsize=1)
def _get_client():
    kwargs = {"region_name": AWS_REGION}
    if MODE == "build":
        endpoint = os.getenv("LOCALSTACK_ENDPOINT", "").strip()
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        kwargs.update({
            "aws_access_key_id":     os.getenv("AWS_ACCESS_KEY_ID", "test"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        })
    return boto3.client("s3", **kwargs)


def upload_resume(user_id: str, file_bytes: bytes, filename: str) -> str:
    key = f"resumes/{_sanitize_id(user_id)}/{_sanitize_filename(filename)}"
    _get_client().put_object(Bucket=BUCKET, Key=key, Body=file_bytes, ContentType="application/pdf")
    return key


def get_resume_bytes(key: str) -> bytes:
    return _get_client().get_object(Bucket=BUCKET, Key=key)["Body"].read()


def upload_evidence(user_id: str, evidence_id: str, data: bytes) -> str:
    key = f"evidence/{_sanitize_id(user_id)}/{_sanitize_id(evidence_id)}.json"
    _get_client().put_object(Bucket=BUCKET, Key=key, Body=data, ContentType="application/json")
    return key


def get_presigned_url(key: str, expires: int = 3600) -> str:
    return _get_client().generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=expires
    )
