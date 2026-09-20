from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import SkillBridgeState
from app.graph.nodes.job import analyze_job
from app.graph.nodes.resume import analyze_resume
from app.graph.nodes.github import analyze_github
from app.graph.nodes.skills import build_skill_profile, calculate_skill_gap
from app.graph.nodes.planner import generate_task
from app.graph.nodes.evaluator import evaluate_submission
from app.graph.nodes.evidence import verify_evidence, decide_next_action

checkpointer = MemorySaver()


def _route_after_evidence(state: SkillBridgeState) -> str:
    return decide_next_action(state)


def build_analysis_graph():
    g = StateGraph(SkillBridgeState)
    g.add_node("analyze_job",         analyze_job)
    g.add_node("analyze_resume",      analyze_resume)
    g.add_node("analyze_github",      analyze_github)
    g.add_node("build_skill_profile", build_skill_profile)
    g.add_node("calculate_skill_gap", calculate_skill_gap)
    g.add_node("generate_task",       generate_task)

    g.set_entry_point("analyze_job")
    g.add_edge("analyze_job",         "analyze_resume")
    g.add_edge("analyze_resume",      "analyze_github")
    g.add_edge("analyze_github",      "build_skill_profile")
    g.add_edge("build_skill_profile", "calculate_skill_gap")
    g.add_edge("calculate_skill_gap", "generate_task")
    g.add_edge("generate_task",       END)
    return g.compile(checkpointer=checkpointer)


def build_eval_graph():
    g = StateGraph(SkillBridgeState)
    g.add_node("evaluate_submission", evaluate_submission)
    g.add_node("verify_evidence",     verify_evidence)
    g.add_node("generate_task",       generate_task)

    g.set_entry_point("evaluate_submission")
    g.add_edge("evaluate_submission", "verify_evidence")
    g.add_conditional_edges(
        "verify_evidence",
        _route_after_evidence,
        {"generate_task": "generate_task", "end": END},
    )
    g.add_edge("generate_task", END)
    return g.compile(checkpointer=checkpointer)


agent      = build_analysis_graph()
eval_agent = build_eval_graph()
