"""
SkillBridge Strands Agent (BUILD IT track).

Uses Strands Agents SDK — AWS open-source agent framework.
Implements the full agentic loop:

  GOAL → AGENT → TOOL SELECTION → TOOL EXECUTION → OBSERVATION → STATE → AGENT

The agent:
  1. Receives student goal + inputs
  2. Decides which tool to call
  3. Observes tool results
  4. Updates state
  5. Decides next action
  6. Loops until project is generated
"""
import json
from typing import Dict, Any, List, Optional

from app.agent.tools import (
    analyze_job,
    extract_job_skills,
    analyze_resume,
    analyze_github,
    search_skills,
    build_skill_profile,
    calculate_skill_gap,
    prioritize_gap,
    generate_project,
    analyze_submission,
    run_tests,
    review_code,
    create_evidence,
    verify_skill,
    get_next_action,
)


class AgentObservation:
    def __init__(self, tool: str, result: Any, success: bool = True, error: str = ""):
        self.tool    = tool
        self.result  = result
        self.success = success
        self.error   = error

    def to_dict(self) -> Dict[str, Any]:
        return {"tool": self.tool, "success": self.success, "result": self.result, "error": self.error}


class SkillBridgeAgent:
    """
    Strands-style agentic loop.
    Each step: decide tool → execute → observe → update state → decide next.
    """

    def __init__(self):
        self.observations: List[AgentObservation] = []
        self.state: Dict[str, Any] = {}

    def _log(self, msg: str) -> None:
        print(f"   🤖 [agent] {msg}")

    def _observe(self, tool: str, result: Any, success: bool = True, error: str = "") -> AgentObservation:
        obs = AgentObservation(tool, result, success, error)
        self.observations.append(obs)
        status = "✅" if success else "❌"
        self._log(f"{status} {tool} → {str(result)[:80]}...")
        return obs

    # ── Analysis pipeline ──────────────────────────────────────────────────────

    def run_analysis(
        self,
        user_id: str,
        target_role: str,
        job_description: str,
        resume_text: str = "",
        github_username: Optional[str] = None,
        target_company: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full analysis pipeline.
        Returns skill_profile, skill_gaps, project.
        """
        self._log(f"Starting analysis for '{target_role}'")
        self.state = {"user_id": user_id, "target_role": target_role}

        # Step 1: Analyze job
        self._log("Tool: analyze_job")
        try:
            job_req = analyze_job(job_description)
            self._observe("analyze_job", job_req)
            self.state["job_requirements"] = job_req
        except Exception as e:
            self._observe("analyze_job", {}, False, str(e))
            return {"error": f"Job analysis failed: {e}"}

        # Step 2: Extract job skills + enrich from OpenSearch
        job_skills = extract_job_skills(job_req)
        self._log(f"Tool: search_skills ({len(job_skills)} skills to enrich)")
        skill_defs = {}
        for skill in job_skills[:5]:  # cap to avoid rate limits
            results = search_skills(skill["name"])
            if results:
                skill_defs[skill["name"].lower()] = results[0]
        self._observe("search_skills", skill_defs)
        self.state["skill_definitions"] = skill_defs

        # Step 3: Analyze resume
        self._log("Tool: analyze_resume")
        try:
            resume_data = analyze_resume(resume_text)
            self._observe("analyze_resume", resume_data)
            self.state["resume_data"] = resume_data
        except Exception as e:
            self._observe("analyze_resume", {}, False, str(e))
            resume_data = {"skills": [], "projects": [], "experience": [], "education": []}
            self.state["resume_data"] = resume_data

        # Step 4: Analyze GitHub
        github_data: Dict[str, Any] = {}
        if github_username:
            self._log(f"Tool: analyze_github ({github_username})")
            try:
                github_data = analyze_github(github_username)
                self._observe("analyze_github", github_data)
            except Exception as e:
                self._observe("analyze_github", {}, False, str(e))
        self.state["github_data"] = github_data

        # Step 5: Build skill profile (evidence-first)
        self._log("Tool: build_skill_profile")
        profile = build_skill_profile(job_skills, resume_data, github_data)
        self._observe("build_skill_profile", profile)
        self.state["skill_profile"] = profile

        # Step 6: Calculate gaps
        self._log("Tool: calculate_skill_gap")
        gaps = calculate_skill_gap(profile)
        self._observe("calculate_skill_gap", gaps)
        self.state["skill_gaps"] = gaps

        # Step 7: Prioritize
        self._log("Tool: prioritize_gap")
        top_gaps = prioritize_gap(gaps)
        self._observe("prioritize_gap", top_gaps)

        # Step 8: Generate project
        self._log("Tool: generate_project")
        try:
            project = generate_project(target_role, top_gaps)
            self._observe("generate_project", project)
            self.state["project"] = project
        except Exception as e:
            self._observe("generate_project", {}, False, str(e))
            return {"error": f"Project generation failed: {e}"}

        self._log("Analysis complete ✅")
        return {
            "skill_profile": profile,
            "skill_gaps":    gaps,
            "project":       project,
            "observations":  [o.to_dict() for o in self.observations],
        }

    # ── Evaluation pipeline ────────────────────────────────────────────────────

    def run_evaluation(
        self,
        user_id: str,
        submission_url: str,
        project: Dict[str, Any],
        skill_gaps: List[Dict[str, Any]],
        skill_profile: Dict[str, Any],
        existing_evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluation pipeline.
        Returns review_result, new evidence, updated skill_profile, next_action.
        """
        self._log(f"Starting evaluation for {submission_url}")

        # Parse owner/repo
        parts = submission_url.rstrip("/").split("/")
        if len(parts) < 2:
            return {"error": "Invalid GitHub URL"}
        owner, repo = parts[-2], parts[-1]

        # Step 1: Get repo files
        self._log("Tool: get_repository_files")
        from app.agent.tools import get_repository_files
        files = get_repository_files(owner, repo)
        self._observe("get_repository_files", files)

        # Step 2: Run static test detection
        self._log("Tool: run_tests")
        test_result = run_tests(files)
        self._observe("run_tests", test_result)

        # Step 3: Code review
        self._log("Tool: review_code")
        code_review = review_code(owner, repo)
        self._observe("review_code", code_review)

        # Step 4: Full submission analysis
        self._log("Tool: analyze_submission")
        try:
            review = analyze_submission(owner, repo, project)
            self._observe("analyze_submission", review)
        except Exception as e:
            self._observe("analyze_submission", {}, False, str(e))
            return {"error": f"Submission analysis failed: {e}"}

        # Step 5: Create evidence for demonstrated skills
        self._log("Tool: create_evidence")
        new_evidence = []
        checks = review.get("deterministic_checks", {})
        for skill_result in review.get("skills_demonstrated", []):
            if skill_result.get("demonstrated"):
                ev = create_evidence(
                    user_id=user_id,
                    skill=skill_result["skill"],
                    level=skill_result.get("level", 3),
                    submission_url=submission_url,
                    project_name=project.get("project_name", ""),
                    review_score=review.get("overall_score", 3),
                    checks=checks,
                )
                new_evidence.append(ev)
                self._observe("create_evidence", ev)

        # Step 6: Update skill profile
        all_evidence = existing_evidence + new_evidence
        updated_profile = dict(skill_profile)
        for ev in new_evidence:
            key = ev["skill"].lower().replace(" ", "_")
            if key in updated_profile:
                updated_profile[key]["current_level"]   = ev["level"]
                updated_profile[key]["evidence_status"] = "demonstrated"
                updated_profile[key].setdefault("evidence_repos", []).append(submission_url)
                try:
                    from app.services.dynamodb import save_skill
                    save_skill(user_id, key, updated_profile[key])
                except Exception:
                    pass

        # Step 7: Decide next action
        self._log("Tool: get_next_action")
        recalculated_gaps = calculate_skill_gap(updated_profile)
        next_act = get_next_action(recalculated_gaps, all_evidence)
        self._observe("get_next_action", next_act)

        # Step 8: Generate next project if gaps remain
        next_project = {}
        if next_act["action"] == "generate_project":
            self._log("Tool: generate_project (next gap)")
            next_top = prioritize_gap(recalculated_gaps)
            try:
                next_project = generate_project(
                    self.state.get("target_role", "Software Engineer"), next_top
                )
                self._observe("generate_project", next_project)
            except Exception as e:
                self._observe("generate_project", {}, False, str(e))

        self._log("Evaluation complete ✅")
        return {
            "review_result":   review,
            "evidence":        new_evidence,
            "skill_profile":   updated_profile,
            "next_action":     next_act,
            "next_project":    next_project,
            "observations":    [o.to_dict() for o in self.observations],
        }
