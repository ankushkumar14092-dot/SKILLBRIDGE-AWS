from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AnalyzeRequest(BaseModel):
    user_id: Optional[str] = None
    target_role: str
    target_company: Optional[str] = None
    target_job_url: Optional[str] = None
    job_description: str
    resume_text: Optional[str] = ""
    github_username: Optional[str] = None


class SubmitRequest(BaseModel):
    thread_id: str
    submission_url: str


class MessageRequest(BaseModel):
    thread_id: str
    message: str


class AnalyzeResponse(BaseModel):
    thread_id: str
    skill_gaps: List[Dict[str, Any]]
    project: Dict[str, Any]
    skill_profile: Dict[str, Any]


class SubmitResponse(BaseModel):
    thread_id: str
    review_result: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    skill_profile: Dict[str, Any]


class StateResponse(BaseModel):
    thread_id: str
    target_role: str
    skill_profile: Dict[str, Any]
    skill_gaps: List[Dict[str, Any]]
    project: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    next_action: str
    error: Optional[str]
