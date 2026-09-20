import os
import requests
from typing import List, Dict, Any, Optional

GITHUB_API = "https://api.github.com"
_TOKEN = os.getenv("GITHUB_TOKEN")


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    return h


def get_user_repos(username: str, limit: int = 20) -> List[Dict[str, Any]]:
    r = requests.get(
        f"{GITHUB_API}/users/{username}/repos",
        params={"per_page": limit, "sort": "updated"},
        headers=_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_repo_tree(owner: str, repo: str) -> List[str]:
    r = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD",
        params={"recursive": "1"},
        headers=_headers(),
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return [f["path"] for f in r.json().get("tree", []) if f["type"] == "blob"]


def get_readme(owner: str, repo: str) -> str:
    r = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/readme",
        headers={**_headers(), "Accept": "application/vnd.github.raw"},
        timeout=10,
    )
    return r.text if r.status_code == 200 else ""


def get_languages(owner: str, repo: str) -> Dict[str, int]:
    r = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/languages",
        headers=_headers(),
        timeout=10,
    )
    return r.json() if r.status_code == 200 else {}


def has_tests(file_paths: List[str]) -> bool:
    test_indicators = ["test", "spec", "__tests__", "tests/"]
    return any(
        any(ind in p.lower() for ind in test_indicators)
        for p in file_paths
    )


def has_ci(file_paths: List[str]) -> bool:
    return any(".github/workflows" in p for p in file_paths)


def build_repo_summary(username: str) -> Dict[str, Any]:
    repos = get_user_repos(username)
    summaries = []
    for r in repos:
        owner = r["owner"]["login"]
        repo = r["name"]
        files = get_repo_tree(owner, repo)
        summaries.append({
            "name": repo,
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "topics": r.get("topics", []),
            "stars": r.get("stargazers_count", 0),
            "has_tests": has_tests(files),
            "has_ci": has_ci(files),
            "files": files[:50],  # cap for LLM context
        })
    return {"username": username, "repos": summaries, "total": len(summaries)}
