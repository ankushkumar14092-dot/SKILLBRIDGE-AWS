"""
DynamoDB service — single-table design.

BUILD IT → LocalStack at LOCALSTACK_ENDPOINT (or moto in-memory)
SHIP IT  → Real AWS DynamoDB
"""
import os
import re
import boto3
from typing import Dict, Any, Optional
from boto3.dynamodb.conditions import Key

MODE               = os.getenv("MODE", "build").lower()
TABLE_NAME         = os.getenv("DYNAMODB_TABLE", "skillbridge")
AWS_REGION         = os.getenv("AWS_REGION", "us-east-1")
LOCALSTACK_ENDPOINT= os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")

_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
_table = None


def _sanitize(v: str) -> str:
    if not _ID_RE.match(str(v)):
        raise ValueError(f"Invalid identifier: {v!r}")
    return v


def _get_table():
    global _table
    if _table is None:
        kwargs: Dict[str, Any] = {"region_name": AWS_REGION}
        if MODE == "build":
            endpoint = os.getenv("LOCALSTACK_ENDPOINT", "").strip()
            if endpoint:
                kwargs["endpoint_url"] = endpoint
            kwargs.update({
                "aws_access_key_id":     os.getenv("AWS_ACCESS_KEY_ID", "test"),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
            })
        _table = boto3.resource("dynamodb", **kwargs).Table(TABLE_NAME)
    return _table


def reset_table() -> None:
    """Called by moto context to reset the cached table reference."""
    global _table
    _table = None


from decimal import Decimal


def _to_decimal(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(v) for v in obj]
    return obj


def _from_decimal(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj) if "." in str(obj) else int(obj)
    if isinstance(obj, dict):
        return {k: _from_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_decimal(v) for v in obj]
    return obj


# ── CRUD ───────────────────────────────────────────────────────────────────────

def put_item(pk: str, sk: str, data: Dict[str, Any]) -> None:
    _get_table().put_item(Item={"PK": pk, "SK": sk, **_to_decimal(data)})


def get_item(pk: str, sk: str) -> Optional[Dict[str, Any]]:
    item = _get_table().get_item(Key={"PK": pk, "SK": sk}).get("Item")
    return _from_decimal(item) if item else None


def query_items(pk: str, sk_prefix: str) -> list:
    resp = _get_table().query(
        KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix)
    )
    return [_from_decimal(it) for it in resp.get("Items", [])]


# ── Domain helpers ─────────────────────────────────────────────────────────────

def save_profile(user_id: str, data: Dict[str, Any]) -> None:
    put_item(f"USER#{_sanitize(user_id)}", "PROFILE", data)


def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    return get_item(f"USER#{_sanitize(user_id)}", "PROFILE")


def save_skill(user_id: str, skill_key: str, data: Dict[str, Any]) -> None:
    put_item(f"USER#{_sanitize(user_id)}", f"SKILL#{skill_key}", data)


def get_skills(user_id: str) -> list:
    return query_items(f"USER#{_sanitize(user_id)}", "SKILL#")


def save_project(user_id: str, project_id: str, data: Dict[str, Any]) -> None:
    put_item(f"USER#{_sanitize(user_id)}", f"PROJECT#{_sanitize(project_id)}", data)


def get_project(user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
    return get_item(f"USER#{_sanitize(user_id)}", f"PROJECT#{_sanitize(project_id)}")


def save_evidence(user_id: str, evidence_id: str, data: Dict[str, Any]) -> None:
    put_item(f"USER#{_sanitize(user_id)}", f"EVIDENCE#{evidence_id}", data)


def get_evidence(user_id: str) -> list:
    return query_items(f"USER#{_sanitize(user_id)}", "EVIDENCE#")
