import uuid
from fastapi import APIRouter, HTTPException
from app.models import AnalyzeRequest, SubmitRequest
from app.graph.graph import agent, eval_agent
from app.agent.strands_agent import SkillBridgeAgent
from app.services.cedar import authorize_or_raise

router = APIRouter(prefix="/agent", tags=["agent"])

EMPTY_STATE = {
    "job_requirements": {}, "resume_data": {}, "github_data": {},
    "skill_definitions": {}, "related_skills": {},
    "skill_profile": {}, "skill_gaps": [], "current_task": {},
    "project": {}, "submission_url": None, "review_result": {},
    "evidence": [], "messages": [], "next_action": "analyze_job", "error": None,
}


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Full BUILD IT agentic pipeline:
    Job → Resume → GitHub → Skill Profile → Gap → Project
    Uses Strands agent loop with 15 tools + OpenSearch skill intelligence.
    """
    thread_id = str(uuid.uuid4())
    user_id   = req.user_id or thread_id

    # Cedar: user can only analyze their own profile
    try:
        authorize_or_raise(user_id, "update", "Profile", user_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Run Strands agent (real agentic loop with observations)
    strands = SkillBridgeAgent()
    agent_result = strands.run_analysis(
        user_id=user_id,
        target_role=req.target_role,
        job_description=req.job_description,
        resume_text=req.resume_text or "",
        github_username=req.github_username,
        target_company=req.target_company,
    )

    if agent_result.get("error"):
        raise HTTPException(status_code=400, detail=agent_result["error"])

    # Also persist state in LangGraph checkpointer for /submit
    initial_state = {
        **EMPTY_STATE,
        "user_id":        user_id,
        "target_role":    req.target_role,
        "target_company": req.target_company,
        "target_job_url": req.target_job_url,
        "job_description":req.job_description,
        "resume_text":    req.resume_text or "",
        "github_username":req.github_username,
        "skill_profile":  agent_result.get("skill_profile", {}),
        "skill_gaps":     agent_result.get("skill_gaps", []),
        "project":        agent_result.get("project", {}),
    }
    config = {"configurable": {"thread_id": thread_id}}
    agent.invoke(initial_state, config)

    return {
        "thread_id":    thread_id,
        "user_id":      user_id,
        "skill_gaps":   agent_result.get("skill_gaps", []),
        "project":      agent_result.get("project", {}),
        "skill_profile":agent_result.get("skill_profile", {}),
        "observations": agent_result.get("observations", []),
    }


@router.post("/submit")
def submit(req: SubmitRequest):
    """
    Evaluation pipeline:
    GitHub Repo → Tests → Code Review → Evidence → Updated Profile → Next Action
    """
    config = {"configurable": {"thread_id": req.thread_id}}
    saved  = agent.get_state(config)
    if not saved or not saved.values:
        raise HTTPException(status_code=404, detail="Thread not found. Run /agent/analyze first.")

    v       = saved.values
    user_id = v.get("user_id", req.thread_id)

    # Cedar: user can only submit their own project
    try:
        authorize_or_raise(user_id, "submit", "Project", user_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Run Strands evaluation agent
    strands = SkillBridgeAgent()
    strands.state = {"target_role": v.get("target_role", "")}
    eval_result = strands.run_evaluation(
        user_id=user_id,
        submission_url=req.submission_url,
        project=v.get("project", {}),
        skill_gaps=v.get("skill_gaps", []),
        skill_profile=v.get("skill_profile", {}),
        existing_evidence=v.get("evidence", []),
    )

    if eval_result.get("error"):
        raise HTTPException(status_code=400, detail=eval_result["error"])

    return {
        "thread_id":    req.thread_id,
        "review_result":eval_result.get("review_result", {}),
        "evidence":     eval_result.get("evidence", []),
        "skill_profile":eval_result.get("skill_profile", {}),
        "next_action":  eval_result.get("next_action", {}),
        "next_project": eval_result.get("next_project", {}),
        "observations": eval_result.get("observations", []),
    }


@router.get("/state/{thread_id}")
def get_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state  = agent.get_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    v = state.values
    return {
        "thread_id":    thread_id,
        "target_role":  v.get("target_role"),
        "skill_profile":v.get("skill_profile", {}),
        "skill_gaps":   v.get("skill_gaps", []),
        "project":      v.get("project", {}),
        "evidence":     v.get("evidence", []),
        "next_action":  v.get("next_action"),
        "error":        v.get("error"),
    }
