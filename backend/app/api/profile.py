from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services import dynamodb as db

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpsert(BaseModel):
    user_id: str
    target_role: Optional[str] = None
    github_username: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@router.get("/{user_id}")
def get_profile(user_id: str):
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/")
def upsert_profile(req: ProfileUpsert):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    db.save_profile(req.user_id, data)
    return {"status": "saved", "user_id": req.user_id}


@router.get("/{user_id}/skills")
def get_skills(user_id: str):
    return {"user_id": user_id, "skills": db.get_skills(user_id)}
