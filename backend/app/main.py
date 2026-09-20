import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent    import router as agent_router
from app.api.profile  import router as profile_router
from app.api.jobs     import router as jobs_router
from app.api.projects import router as projects_router
from app.api.evidence import router as evidence_router
from app.api.resume   import router as resume_router

app = FastAPI(title="SkillBridge AI", version="1.0.0", description="From Claimed Skills to Verified Skills")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(agent_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(projects_router)
app.include_router(evidence_router)
app.include_router(resume_router)


@app.on_event("startup")
def startup():
    # Seed OpenSearch skill definitions (no-op if not running)
    try:
        from app.services.opensearch import index_seed_data
        index_seed_data()
    except Exception:
        pass


@app.get("/health")
def health():
    return {
        "status":   "ok",
        "service":  "SkillBridge AI",
        "mode":     os.getenv("MODE", "build"),
        "llm":      os.getenv("STRANDS_PROVIDER", "mock"),
        "track":    "BUILD IT — First Commit Hackathon",
    }


@app.get("/cedar/policies")
def cedar_policies():
    from app.services.cedar import get_policies
    return {"policies": get_policies()}


# SHIP IT — Mangum Lambda handler
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass
