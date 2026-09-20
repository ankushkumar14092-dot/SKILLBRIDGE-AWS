from app.graph.state import SkillBridgeState
from app.agent.tools import build_skill_profile as _build_profile, calculate_skill_gap as _calc_gap

def build_skill_profile(state: SkillBridgeState) -> SkillBridgeState:
    job_skills = state.get("job_requirements", {}).get("skills", [])
    profile = _build_profile(
        job_skills=job_skills,
        resume_data=state.get("resume_data", {}),
        github_data=state.get("github_data", {}),
    )
    return {**state, "skill_profile": profile, "next_action": "calculate_skill_gap"}

def calculate_skill_gap(state: SkillBridgeState) -> SkillBridgeState:
    gaps = _calc_gap(state.get("skill_profile", {}))
    return {**state, "skill_gaps": gaps, "next_action": "generate_task"}
