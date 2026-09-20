from app.graph.state import SkillBridgeState
from app.agent.tools import analyze_job as _analyze_job

def analyze_job(state: SkillBridgeState) -> SkillBridgeState:
    if not state.get("job_description"):
        return {**state, "error": "job_description is required", "next_action": "error"}
    try:
        result = _analyze_job(state["job_description"])
        return {**state, "job_requirements": result, "next_action": "analyze_resume"}
    except Exception as e:
        return {**state, "error": str(e), "next_action": "error"}
