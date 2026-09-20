from typing import TypedDict, List, Dict, Any, Optional


class SkillBridgeState(TypedDict):
    # Identity
    user_id: str
    target_role: str
    target_company: Optional[str]
    target_job_url: Optional[str]

    # Job analysis
    job_description: str
    job_requirements: Dict[str, Any]       # structured: role, skills[], experience_years

    # Student inputs
    resume_text: str
    resume_data: Dict[str, Any]            # skills[], projects[], experience[], education[]
    github_username: Optional[str]
    github_data: Dict[str, Any]            # skill_evidence{}, repos[], languages[]

    # Skill intelligence (from OpenSearch)
    skill_definitions: Dict[str, Any]      # enriched skill info from OpenSearch
    related_skills: Dict[str, List[str]]   # skill → related skills map

    # Skill profile
    skill_profile: Dict[str, Any]          # key → {name, required_level, current_level, evidence_status}
    skill_gaps: List[Dict[str, Any]]       # sorted by priority_score

    # Project
    project: Dict[str, Any]               # generated project with tasks
    current_task: Dict[str, Any]

    # Submission + evaluation
    submission_url: Optional[str]
    review_result: Dict[str, Any]          # overall_score, skills_demonstrated[], feedback

    # Evidence
    evidence: List[Dict[str, Any]]         # verified evidence records

    # Agent control
    messages: List[Dict[str, Any]]         # agent conversation log
    next_action: str
    error: Optional[str]
