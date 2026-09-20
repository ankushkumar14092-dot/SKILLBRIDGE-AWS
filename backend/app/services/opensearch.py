"""
OpenSearch service — Skill Intelligence Layer (BUILD IT track).

Indexes:
  skills          — skill definitions + relationships
  job_requirements — parsed job skill requirements
  project_templates — project ideas per skill gap
  evidence        — student skill evidence records

The agent uses this to:
  - search what skills a job requires
  - find related skills
  - retrieve project templates for a gap
  - search existing evidence for a student
"""
import os
import json
from typing import Dict, Any, List, Optional

OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "http://localhost:9200")

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from opensearchpy import OpenSearch
            _client = OpenSearch(
                hosts=[OPENSEARCH_ENDPOINT],
                use_ssl=False,
                verify_certs=False,
                timeout=10,
            )
        except Exception:
            _client = None
    return _client


def _available() -> bool:
    c = _get_client()
    if c is None:
        return False
    try:
        return c.ping()
    except Exception:
        return False


# ── Index management ───────────────────────────────────────────────────────────

INDEXES = {
    "skills": {
        "mappings": {
            "properties": {
                "name":          {"type": "keyword"},
                "category":      {"type": "keyword"},
                "description":   {"type": "text"},
                "related_skills":{"type": "keyword"},
                "level_descriptors": {"type": "object"},
            }
        }
    },
    "job_requirements": {
        "mappings": {
            "properties": {
                "job_id":   {"type": "keyword"},
                "role":     {"type": "text"},
                "company":  {"type": "keyword"},
                "skills":   {"type": "keyword"},
                "raw":      {"type": "text"},
            }
        }
    },
    "project_templates": {
        "mappings": {
            "properties": {
                "title":          {"type": "text"},
                "skills_targeted":{"type": "keyword"},
                "difficulty":     {"type": "keyword"},
                "description":    {"type": "text"},
                "tasks":          {"type": "text"},
            }
        }
    },
    "evidence": {
        "mappings": {
            "properties": {
                "user_id":    {"type": "keyword"},
                "skill":      {"type": "keyword"},
                "level":      {"type": "integer"},
                "source_url": {"type": "keyword"},
                "verified":   {"type": "boolean"},
                "created_at": {"type": "date"},
            }
        }
    },
}


def ensure_indexes() -> None:
    c = _get_client()
    if not c:
        return
    for name, body in INDEXES.items():
        try:
            if not c.indices.exists(index=name):
                c.indices.create(index=name, body=body)
                print(f"✅ OpenSearch index '{name}' created")
        except Exception as e:
            print(f"⚠️  OpenSearch index '{name}': {e}")


# ── Skill search ───────────────────────────────────────────────────────────────

def search_skills(query: str, size: int = 5) -> List[Dict[str, Any]]:
    """Search skill definitions — used by agent to understand what a skill means."""
    if not _available():
        return _fallback_skill_search(query)
    c = _get_client()
    try:
        resp = c.search(
            index="skills",
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "description", "related_skills"],
                    }
                },
                "size": size,
            },
        )
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception:
        return _fallback_skill_search(query)


def get_related_skills(skill_name: str) -> List[str]:
    """Get skills related to a given skill — for dependency-aware gap prioritization."""
    if not _available():
        return SKILL_RELATIONSHIPS.get(skill_name.lower(), [])
    c = _get_client()
    try:
        resp = c.search(
            index="skills",
            body={"query": {"term": {"name": skill_name.lower()}}, "size": 1},
        )
        hits = resp["hits"]["hits"]
        if hits:
            return hits[0]["_source"].get("related_skills", [])
    except Exception:
        pass
    return SKILL_RELATIONSHIPS.get(skill_name.lower(), [])


def search_project_templates(skills: List[str], size: int = 3) -> List[Dict[str, Any]]:
    """Find project templates that target specific skill gaps."""
    if not _available():
        return _fallback_project_templates(skills)
    c = _get_client()
    try:
        resp = c.search(
            index="project_templates",
            body={
                "query": {"terms": {"skills_targeted": [s.lower() for s in skills]}},
                "size": size,
            },
        )
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception:
        return _fallback_project_templates(skills)


def index_evidence(evidence: Dict[str, Any]) -> None:
    """Index a new evidence record so it's searchable."""
    if not _available():
        return
    c = _get_client()
    try:
        c.index(index="evidence", id=evidence.get("evidence_id"), body=evidence)
    except Exception as e:
        print(f"⚠️  OpenSearch evidence index: {e}")


def search_evidence(user_id: str, skill: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search evidence for a student, optionally filtered by skill."""
    if not _available():
        return []
    c = _get_client()
    try:
        must = [{"term": {"user_id": user_id}}]
        if skill:
            must.append({"term": {"skill": skill.lower()}})
        resp = c.search(
            index="evidence",
            body={"query": {"bool": {"must": must}}, "size": 50},
        )
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception:
        return []


# ── Seed data ──────────────────────────────────────────────────────────────────

SKILL_DEFINITIONS = [
    {"name": "python",      "category": "programming", "description": "Python programming language — scripting, OOP, data structures", "related_skills": ["fastapi", "django", "testing", "data-structures"]},
    {"name": "fastapi",     "category": "framework",   "description": "FastAPI — modern Python web framework for building REST APIs", "related_skills": ["python", "rest-api", "pydantic", "uvicorn"]},
    {"name": "aws-lambda",  "category": "cloud",       "description": "AWS Lambda — serverless compute, event-driven functions",      "related_skills": ["api-gateway", "dynamodb", "iam", "sam-cli", "serverless"]},
    {"name": "dynamodb",    "category": "database",    "description": "Amazon DynamoDB — NoSQL key-value and document database",      "related_skills": ["aws-lambda", "single-table-design", "boto3"]},
    {"name": "docker",      "category": "devops",      "description": "Docker — containerization, Dockerfile, docker-compose",        "related_skills": ["kubernetes", "ci-cd", "microservices"]},
    {"name": "testing",     "category": "quality",     "description": "Software testing — unit tests, integration tests, pytest",     "related_skills": ["python", "ci-cd", "tdd"]},
    {"name": "rest-api",    "category": "backend",     "description": "REST API design — HTTP methods, status codes, JSON, OpenAPI",  "related_skills": ["fastapi", "authentication", "swagger"]},
    {"name": "git",         "category": "devops",      "description": "Git version control — commits, branches, pull requests",      "related_skills": ["github", "ci-cd"]},
    {"name": "s3",          "category": "cloud",       "description": "Amazon S3 — object storage, file upload, presigned URLs",     "related_skills": ["aws-lambda", "boto3", "iam"]},
    {"name": "api-gateway", "category": "cloud",       "description": "Amazon API Gateway — HTTP/REST/WebSocket API management",     "related_skills": ["aws-lambda", "cognito", "cors"]},
]

PROJECT_TEMPLATES = [
    {
        "title": "Serverless Job Tracker",
        "skills_targeted": ["aws-lambda", "dynamodb", "api-gateway", "fastapi"],
        "difficulty": "intermediate",
        "description": "Build a serverless job application tracker. REST API on Lambda, DynamoDB for storage, API Gateway as the entry point.",
        "tasks": "1. FastAPI CRUD endpoints\n2. DynamoDB single-table schema\n3. Lambda deployment with SAM\n4. API Gateway integration\n5. Unit + integration tests",
    },
    {
        "title": "Dockerized Microservice",
        "skills_targeted": ["docker", "rest-api", "testing", "ci-cd"],
        "difficulty": "intermediate",
        "description": "Build a containerized REST microservice with Docker, health checks, and a CI/CD pipeline.",
        "tasks": "1. FastAPI service\n2. Dockerfile + docker-compose\n3. Health check endpoint\n4. pytest test suite\n5. GitHub Actions CI",
    },
    {
        "title": "GitHub Activity Analyzer",
        "skills_targeted": ["python", "rest-api", "testing", "git"],
        "difficulty": "beginner",
        "description": "Build a Python tool that analyzes GitHub activity and generates a skill report.",
        "tasks": "1. GitHub REST API client\n2. Repository analysis\n3. Skill extraction\n4. Report generation\n5. Tests",
    },
]

# Fallback when OpenSearch is not running
SKILL_RELATIONSHIPS: Dict[str, List[str]] = {
    s["name"]: s["related_skills"] for s in SKILL_DEFINITIONS
}


def _fallback_skill_search(query: str) -> List[Dict[str, Any]]:
    q = query.lower()
    return [s for s in SKILL_DEFINITIONS if q in s["name"] or q in s["description"].lower()][:5]


def _fallback_project_templates(skills: List[str]) -> List[Dict[str, Any]]:
    skill_set = {s.lower() for s in skills}
    scored = []
    for t in PROJECT_TEMPLATES:
        overlap = len(skill_set & set(t["skills_targeted"]))
        if overlap > 0:
            scored.append((overlap, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:3]]


def index_seed_data() -> None:
    """Index all seed skill definitions and project templates into OpenSearch."""
    if not _available():
        print("⚠️  OpenSearch not available — seed data skipped (fallback active)")
        return
    ensure_indexes()
    c = _get_client()
    for skill in SKILL_DEFINITIONS:
        try:
            c.index(index="skills", id=skill["name"], body=skill)
        except Exception as e:
            print(f"⚠️  Skill index {skill['name']}: {e}")
    for i, tmpl in enumerate(PROJECT_TEMPLATES):
        try:
            c.index(index="project_templates", id=str(i), body=tmpl)
        except Exception as e:
            print(f"⚠️  Template index {i}: {e}")
    print(f"✅ OpenSearch: indexed {len(SKILL_DEFINITIONS)} skills, {len(PROJECT_TEMPLATES)} templates")
