import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services import dynamodb as db
from app.tools import generate_project, prioritize_skill

router = APIRouter(prefix="/projects", tags=["projects"])


class GenerateProjectRequest(BaseModel):
    user_id: str
    target_role: str
    skill_gaps: List[Dict[str, Any]]


@router.post("/generate")
def create_project(req: GenerateProjectRequest):
    top_gaps = prioritize_skill(req.skill_gaps)
    project = generate_project(req.target_role, top_gaps)
    project_id = str(uuid.uuid4())
    project["project_id"] = project_id
    db.save_project(req.user_id, project_id, project)
    return {"project_id": project_id, "project": project}


@router.get("/{user_id}/{project_id}")
def get_project(user_id: str, project_id: str):
    project = db.get_project(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
