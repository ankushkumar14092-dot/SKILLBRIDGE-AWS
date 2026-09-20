from app.graph.state import SkillBridgeState
from app.agent.tools import create_evidence, get_next_action, calculate_skill_gap

def verify_evidence(state: SkillBridgeState) -> SkillBridgeState:
    review   = state.get("review_result", {})
    project  = state.get("project", {})
    existing = state.get("evidence", [])
    checks   = review.get("deterministic_checks", {})

    new_evidence = []
    for s in review.get("skills_demonstrated", []):
        if s.get("demonstrated"):
            ev = create_evidence(
                user_id=state.get("user_id", "unknown"),
                skill=s["skill"],
                level=s.get("level", 3),
                submission_url=state.get("submission_url", ""),
                project_name=project.get("project_name", ""),
                review_score=review.get("overall_score", 3),
                checks=checks,
            )
            new_evidence.append(ev)

    skill_profile = dict(state.get("skill_profile", {}))
    for ev in new_evidence:
        key = ev["skill"].lower().replace(" ", "_")
        if key in skill_profile:
            skill_profile[key]["current_level"]   = ev["level"]
            skill_profile[key]["evidence_status"] = "demonstrated"

    return {
        **state,
        "evidence":      existing + new_evidence,
        "skill_profile": skill_profile,
        "next_action":   "decide_next_action",
    }

def decide_next_action(state: SkillBridgeState) -> str:
    updated_gaps = calculate_skill_gap(state.get("skill_profile", {}))
    result = get_next_action(updated_gaps, state.get("evidence", []))
    return "generate_task" if result["action"] == "generate_project" else "end"
