from fastapi import APIRouter
from pydantic import BaseModel
from app.tools import analyze_job_description, extract_job_skills

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobAnalyzeRequest(BaseModel):
    job_description: str


@router.post("/analyze")
def analyze_job(req: JobAnalyzeRequest):
    requirements = analyze_job_description(req.job_description)
    skills = extract_job_skills(requirements)
    return {"requirements": requirements, "skills": skills}
