from app.graph.state import SkillBridgeState
from app.agent.tools import generate_project, prioritize_gap

def generate_task(state: SkillBridgeState) -> SkillBridgeState:
    gaps = state.get("skill_gaps", [])
    if not gaps:
        return {**state, "next_action": "end"}
    top_gaps = prioritize_gap(gaps)
    try:
        project = generate_project(state.get("target_role", "Software Engineer"), top_gaps)
        return {**state, "project": project, "current_task": project, "next_action": "wait_for_submission"}
    except Exception as e:
        return {**state, "error": str(e), "next_action": "end"}
