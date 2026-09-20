"""
SkillBridge AI — BUILD IT local runner
No AWS account. No Docker required.

Strategy:
  1. Try LocalStack at localhost:4566  (if Docker is running)
  2. Fall back to moto in-memory mock  (always works, zero setup)

Usage:
  python local_runner.py
"""
import os, sys

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv("../.env")
except Exception:
    pass

os.environ.setdefault("MODE",                   "build")
os.environ.setdefault("AWS_REGION",             "us-east-1")
os.environ.setdefault("AWS_DEFAULT_REGION",     "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID",      "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY",  "test")
os.environ.setdefault("DYNAMODB_TABLE",         "skillbridge")
os.environ.setdefault("S3_BUCKET",              "skillbridge-resumes")
os.environ.setdefault("STRANDS_PROVIDER",       "mock")

import boto3
import requests as http_req
from unittest.mock import patch

LOCALSTACK = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")

# ── Mock LLM responses ─────────────────────────────────────────────────────────

MOCK_RESPONSES = {
    "job": {
        "role": "Backend Engineer Intern", "company": "AWS",
        "skills": [
            {"name": "Python",     "required_level": 4, "importance": 0.9, "category": "programming"},
            {"name": "FastAPI",    "required_level": 3, "importance": 0.8, "category": "framework"},
            {"name": "DynamoDB",   "required_level": 3, "importance": 0.75,"category": "database"},
            {"name": "AWS Lambda", "required_level": 3, "importance": 0.8, "category": "cloud"},
            {"name": "Docker",     "required_level": 2, "importance": 0.6, "category": "devops"},
            {"name": "Testing",    "required_level": 3, "importance": 0.7, "category": "quality"},
        ],
        "experience_years": 0,
        "key_responsibilities": ["Build REST APIs", "Design DynamoDB schemas", "Deploy on Lambda"],
    },
    "resume": {
        "skills": ["Python", "Flask", "SQL", "Git"],
        "projects": [{"name": "Blog API", "technologies": ["Python", "Flask"], "description": "REST API"}],
        "experience": [],
        "education": [{"degree": "B.Tech CS", "institution": "University"}],
    },
    "github": {
        "languages": ["Python", "JavaScript"],
        "skill_evidence": {
            "python":  {"evidence_level": 3, "repos": ["blog-api"], "evidence_type": "implementation"},
            "git":     {"evidence_level": 3, "repos": ["blog-api"], "evidence_type": "commits"},
            "fastapi": {"evidence_level": 1, "repos": [],           "evidence_type": "partial"},
        },
        "total_repos": 6,
        "highlights": ["Active Python developer", "REST API experience"],
    },
    "project": {
        "project_name": "Serverless Job Tracker",
        "description":  "Build a serverless job application tracker using FastAPI on AWS Lambda with DynamoDB",
        "skills_tested": ["FastAPI", "AWS Lambda", "DynamoDB", "Docker", "Testing"],
        "tasks": [
            {"id": 1, "title": "FastAPI CRUD endpoints",  "description": "Create /jobs REST endpoints",         "skill": "FastAPI",    "verification_criteria": "GET/POST/PUT/DELETE endpoints exist"},
            {"id": 2, "title": "DynamoDB schema",          "description": "Design single-table schema",          "skill": "DynamoDB",   "verification_criteria": "Table with PK/SK exists"},
            {"id": 3, "title": "Lambda deployment",        "description": "Package with SAM CLI and deploy",     "skill": "AWS Lambda", "verification_criteria": "template.yaml or serverless.yml exists"},
            {"id": 4, "title": "Write tests",              "description": "Unit + integration tests",            "skill": "Testing",    "verification_criteria": "test files present, pytest passes"},
            {"id": 5, "title": "Dockerize",                "description": "Add Dockerfile + docker-compose",     "skill": "Docker",     "verification_criteria": "Dockerfile present"},
        ],
        "architecture":  "FastAPI + AWS Lambda + API Gateway + DynamoDB",
        "estimated_hours": 12,
        "evidence_generated": ["FastAPI proficiency", "DynamoDB schema design", "Lambda deployment", "Testing", "Docker"],
        "requirements_checklist": ["REST endpoints", "DynamoDB integration", "Tests", "README", "Dockerfile"],
    },
    "eval": {
        "overall_score": 4,
        "skills_demonstrated": [
            {"skill": "FastAPI",    "demonstrated": True,  "evidence": "REST endpoints found",          "level": 3},
            {"skill": "DynamoDB",   "demonstrated": True,  "evidence": "Table schema present",          "level": 3},
            {"skill": "Testing",    "demonstrated": True,  "evidence": "pytest files found",            "level": 3},
            {"skill": "AWS Lambda", "demonstrated": False, "evidence": "No SAM/serverless config found","level": 0},
            {"skill": "Docker",     "demonstrated": False, "evidence": "No Dockerfile found",           "level": 0},
        ],
        "feedback":      "Good FastAPI and DynamoDB implementation. Missing Lambda deployment and Docker.",
        "strengths":     ["Clean API design", "Good DynamoDB schema", "Has tests"],
        "improvements":  ["Add SAM template.yaml", "Add Dockerfile"],
        "ready_for_job": False,
        "deterministic_checks": {"has_tests": True, "has_ci": False, "has_readme": True, "file_count": 12},
    },
}

_call_seq = ["job", "resume", "github", "project", "eval"]
_idx = {"n": 0}

def _mock_llm_json(messages, system=""):
    combined = (system + " " + " ".join(str(m.get("content", "")) for m in messages)).lower()
    if "submission" in combined or "evaluate" in combined or "overall_score" in combined:
        key = "eval"
    elif "resume" in combined:
        key = "resume"
    elif "github" in combined:
        key = "github"
    elif "project" in combined or "engineering project" in combined:
        key = "project"
    elif "job" in combined or "responsibilities" in combined or "requirements" in combined:
        key = "job"
    else:
        key = _call_seq[min(_idx["n"], len(_call_seq) - 1)]

    _idx["n"] += 1
    print(f"   🤖 [mock-llm] call #{_idx['n']} → {key}")
    return MOCK_RESPONSES[key]


# ── LocalStack check ───────────────────────────────────────────────────────────

def _localstack_running() -> bool:
    try:
        return http_req.get(f"{LOCALSTACK}/_localstack/health", timeout=2).status_code == 200
    except Exception:
        return False


def _setup_localstack():
    kw = {"region_name": "us-east-1", "endpoint_url": LOCALSTACK,
          "aws_access_key_id": "test", "aws_secret_access_key": "test"}
    ddb = boto3.client("dynamodb", **kw)
    if "skillbridge" not in ddb.list_tables().get("TableNames", []):
        ddb.create_table(
            TableName="skillbridge",
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    s3 = boto3.client("s3", **kw)
    try:
        s3.create_bucket(Bucket="skillbridge-resumes")
    except Exception:
        pass
    print("✅ LocalStack DynamoDB + S3 ready")


# ── Moto fallback ──────────────────────────────────────────────────────────────

def _run_with_moto():
    from moto import mock_aws
    from app.services.dynamodb import reset_table
    from app.services.llm import set_mock_responses

    # When running with in-memory moto (no LocalStack), clear endpoint so moto intercepts all boto3 calls
    os.environ["LOCALSTACK_ENDPOINT"] = ""
    set_mock_responses(MOCK_RESPONSES)

    print("✅ moto in-memory AWS mock active (no Docker needed)")

    @mock_aws
    def _start():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="skillbridge",
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="skillbridge-resumes")
        reset_table()
        print("✅ moto DynamoDB + S3 ready")
        _boot()

    _start()


def _boot():
    provider = os.getenv("STRANDS_PROVIDER", "mock")
    print(f"✅ LLM Provider active: {provider}")
    print("🚀 SkillBridge API → http://localhost:8000")
    print("📖 Docs          → http://localhost:8000/docs")
    print("🔍 OpenSearch    → optional (fallback active if not running)\n")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    provider = os.getenv("STRANDS_PROVIDER", "mock").lower()
    print("\n🔧 SkillBridge AI — BUILD IT local runner")
    print("=" * 45)
    print(f"   LLM provider : {provider}")
    print(f"   AWS services : LocalStack / moto")
    print(f"   OpenSearch   : optional\n")

    def _run_app():
        if _localstack_running():
            print(f"✅ LocalStack detected at {LOCALSTACK}")
            _setup_localstack()
            _boot()
        else:
            print("⚠️  LocalStack not found — using moto in-memory (no Docker needed)")
            _run_with_moto()

    if provider == "mock":
        with patch("app.services.llm.invoke_llm_json", side_effect=_mock_llm_json):
            _run_app()
    else:
        print(f"🔥 Running with REAL LLM provider: {provider}")
        _run_app()
