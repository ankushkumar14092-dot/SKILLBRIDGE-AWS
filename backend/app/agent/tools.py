"""
SkillBridge Agent Tools Module
Re-exports and helper implementations for Strands Agent and LangGraph nodes.
"""
from typing import Dict, Any, List, Optional
from app.tools import (
    analyze_job_description,
    extract_job_skills,
    analyze_resume,
    analyze_github,
    calculate_skill_gap,
    prioritize_skill,
    generate_project,
    analyze_submission,
    run_tests,
    review_code,
    verify_skill,
    get_repository_files,
    list_repositories,
)

# Aliases for function names
analyze_job = analyze_job_description
prioritize_gap = prioritize_skill


def search_skills(query: str) -> List[Dict[str, Any]]:
    return [{"name": query, "category": "general"}]


def build_skill_profile(
    job_skills: List[Dict[str, Any]],
    resume_data: Dict[str, Any],
    github_data: Dict[str, Any],
) -> Dict[str, Any]:
    profile = {}
    resume_skills = set(resume_data.get("skills", []))
    github_langs = set(github_data.get("languages", []))

    for skill in job_skills:
        name = skill.get("name", "Unknown")
        key = name.lower().replace(" ", "_")
        req_level = skill.get("required_level", 3)

        # Estimate current level based on resume/github presence
        current_level = 1
        if name.lower() in [s.lower() for s in resume_skills]:
            current_level += 1
        if name.lower() in [l.lower() for l in github_langs]:
            current_level += 1

        profile[key] = {
            "name": name,
            "required_level": req_level,
            "current_level": current_level,
            "importance": skill.get("importance", 0.8),
            "category": skill.get("category", "core"),
            "evidence_status": "unverified" if current_level < req_level else "demonstrated",
        }
    return profile


def create_evidence(
    user_id: str,
    skill: str,
    level: int = 3,
    submission_url: str = "",
    project_name: str = "",
    review_score: int = 3,
    checks: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "skill": skill,
        "level": level,
        "submission_url": submission_url,
        "project_name": project_name,
        "review_score": review_score,
        "checks": checks or {},
        "status": "verified",
    }


def get_next_action(gaps: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    if gaps:
        return {"action": "generate_project", "reason": f"Found {len(gaps)} skill gaps to address"}
    return {"action": "complete", "reason": "All skills demonstrated"}
