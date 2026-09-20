"""
12 core tools for SkillBridge agent.
Each tool is a plain callable — no LangChain decorator needed for MVP.
"""

import io
import pdfplumber
from typing import Dict, Any, List

from app.services.bedrock import invoke_llm_json
from app.services import github as gh_service


# ── Job tools ──────────────────────────────────────────────────────────────────

def analyze_job_description(job_description: str) -> Dict[str, Any]:
    return invoke_llm_json(
        messages=[{"role": "user", "content": f"Extract structured job requirements.\n\n{job_description}"}],
        system=(
            "Return ONLY valid JSON:\n"
            '{"role":"string","company":"string","skills":[{"name":"string","required_level":1,"importance":0.9,"category":"string"}],'
            '"experience_years":0,"key_responsibilities":["string"]}'
        ),
    )


def extract_job_skills(job_requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    return job_requirements.get("skills", [])


# ── Student tools ──────────────────────────────────────────────────────────────

def analyze_resume(resume_text: str) -> Dict[str, Any]:
    if not resume_text:
        return {"skills": [], "projects": [], "experience": [], "education": []}
    return invoke_llm_json(
        messages=[{"role": "user", "content": f"Extract structured information from this resume.\n\n{resume_text}"}],
        system=(
            "Return ONLY valid JSON:\n"
            '{"skills":["string"],"projects":[{"name":"string","technologies":["string"],"description":"string"}],'
            '"experience":[{"role":"string","company":"string","duration":"string"}],'
            '"education":[{"degree":"string","institution":"string"}]}'
        ),
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text = []
    with io.BytesIO(pdf_bytes) as buf:
        with pdfplumber.open(buf) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
    return "\n".join(text)


def get_student_profile(user_id: str) -> Dict[str, Any]:
    from app.services.dynamodb import get_profile
    return get_profile(user_id) or {}


# ── GitHub tools ───────────────────────────────────────────────────────────────

def get_github_profile(username: str) -> Dict[str, Any]:
    repos = gh_service.get_user_repos(username, limit=5)
    return {
        "username": username,
        "public_repos": len(repos),
        "languages": list({r.get("language") for r in repos if r.get("language")}),
    }


def list_repositories(username: str) -> List[Dict[str, Any]]:
    return gh_service.get_user_repos(username)


def get_repository_files(owner: str, repo: str) -> List[str]:
    return gh_service.get_repo_tree(owner, repo)


def analyze_github(username: str) -> Dict[str, Any]:
    summary = gh_service.build_repo_summary(username)
    return invoke_llm_json(
        messages=[{"role": "user", "content": f"Analyze these repos and extract skill evidence.\n\n{summary['repos']}"}],
        system=(
            "Return ONLY valid JSON:\n"
            '{"languages":["string"],"skill_evidence":{"skill_name":{"evidence_level":1,"repos":["string"]}},'
            '"total_repos":0,"highlights":["string"]}'
        ),
    )


# ── Skill tools ────────────────────────────────────────────────────────────────

def calculate_skill_gap(skill_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    gaps = [
        {
            "skill": skill["name"],
            "key": key,
            "required_level": skill["required_level"],
            "current_level": skill["current_level"],
            "gap": skill["required_level"] - skill["current_level"],
            "importance": skill["importance"],
            "priority_score": round(skill["importance"] * (skill["required_level"] - skill["current_level"]), 2),
            "category": skill.get("category", "general"),
        }
        for key, skill in skill_profile.items()
        if skill["required_level"] - skill["current_level"] > 0
    ]
    return sorted(gaps, key=lambda x: x["priority_score"], reverse=True)


def prioritize_skill(gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return gaps[:3]


# ── Project tools ──────────────────────────────────────────────────────────────

def generate_project(target_role: str, top_gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    return invoke_llm_json(
        messages=[{
            "role": "user",
            "content": f"Target role: {target_role}\nTop skill gaps: {top_gaps}\n\nGenerate a practical engineering project.",
        }],
        system=(
            "Return ONLY valid JSON:\n"
            '{"project_name":"string","description":"string","skills_tested":["string"],'
            '"tasks":[{"id":1,"title":"string","description":"string","skill":"string"}],'
            '"architecture":"string","estimated_hours":0,"evidence_generated":["string"]}'
        ),
    )


def generate_task(project: Dict[str, Any], completed_task_ids: List[int]) -> Dict[str, Any]:
    tasks = project.get("tasks", [])
    pending = [t for t in tasks if t["id"] not in completed_task_ids]
    return pending[0] if pending else {}


# ── Verification tools ─────────────────────────────────────────────────────────

def analyze_submission(owner: str, repo: str, project: Dict[str, Any]) -> Dict[str, Any]:
    files = gh_service.get_repo_tree(owner, repo)
    return invoke_llm_json(
        messages=[{
            "role": "user",
            "content": f"Project requirements: {project}\n\nSubmitted files:\n{files}\n\nEvaluate this submission.",
        }],
        system=(
            "Return ONLY valid JSON:\n"
            '{"overall_score":1,"skills_demonstrated":[{"skill":"string","demonstrated":true,"evidence":"string","level":1}],'
            '"feedback":"string","strengths":["string"],"improvements":["string"],"ready_for_job":false}'
        ),
    )


def run_tests(file_paths: List[str]) -> Dict[str, Any]:
    test_files = [f for f in file_paths if "test" in f.lower() or "spec" in f.lower()]
    return {"test_files_found": len(test_files), "has_tests": len(test_files) > 0, "files": test_files}


def review_code(owner: str, repo: str) -> Dict[str, Any]:
    files = gh_service.get_repo_tree(owner, repo)
    languages = gh_service.get_languages(owner, repo)
    return {
        "languages": list(languages.keys()),
        "has_tests": gh_service.has_tests(files),
        "has_ci": gh_service.has_ci(files),
        "file_count": len(files),
        "readme_present": any("readme" in f.lower() for f in files),
    }


def verify_skill(skill: str, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    matching = [e for e in evidence_list if e.get("skill", "").lower() == skill.lower()]
    return {
        "skill": skill,
        "verified": len(matching) > 0,
        "evidence_count": len(matching),
        "max_level": max((e.get("level", 0) for e in matching), default=0),
    }
