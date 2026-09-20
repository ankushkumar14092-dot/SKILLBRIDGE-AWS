from app.graph.state import SkillBridgeState
from app.agent.tools import analyze_resume as _analyze_resume

def analyze_resume(state: SkillBridgeState) -> SkillBridgeState:
    try:
        result = _analyze_resume(state.get("resume_text", ""))
        return {**state, "resume_data": result, "next_action": "analyze_github"}
    except Exception as e:
        return {**state, "resume_data": {}, "error": str(e), "next_action": "analyze_github"}
