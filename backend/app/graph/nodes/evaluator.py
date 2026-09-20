from app.graph.state import SkillBridgeState
from app.agent.tools import analyze_submission

def evaluate_submission(state: SkillBridgeState) -> SkillBridgeState:
    submission_url = state.get("submission_url")
    if not submission_url:
        return {**state, "next_action": "wait_for_submission"}
    parts = submission_url.rstrip("/").split("/")
    if len(parts) < 2:
        return {**state, "error": "Invalid GitHub URL", "next_action": "end"}
    owner, repo = parts[-2], parts[-1]
    try:
        result = analyze_submission(owner, repo, state.get("project", {}))
        return {**state, "review_result": result, "next_action": "verify_evidence"}
    except Exception as e:
        return {**state, "error": str(e), "next_action": "end"}
