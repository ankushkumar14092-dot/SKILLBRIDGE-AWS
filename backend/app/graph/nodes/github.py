from app.graph.state import SkillBridgeState
from app.agent.tools import analyze_github as _analyze_github

def analyze_github(state: SkillBridgeState) -> SkillBridgeState:
    username = state.get("github_username")
    if not username:
        return {**state, "github_data": {}, "next_action": "build_skill_profile"}
    try:
        result = _analyze_github(username)
        return {**state, "github_data": result, "next_action": "build_skill_profile"}
    except Exception as e:
        return {**state, "github_data": {"error": str(e)}, "next_action": "build_skill_profile"}
