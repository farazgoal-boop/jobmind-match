from typing import Dict, List
import requests

from app.config import settings


def fetch_repo_insights(username: str, max_repos: int = 5) -> List[Dict]:
    if not username:
        return []

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page={max_repos}"
    repos_resp = requests.get(repos_url, headers=headers, timeout=20)
    repos_resp.raise_for_status()

    insights = []
    for repo in repos_resp.json():
        repo_name = repo["name"]
        languages = _fetch_languages(username, repo_name, headers)
        commits_count = _fetch_recent_commits_count(username, repo_name, headers)
        insights.append(
            {
                "repo": repo_name,
                "description": repo.get("description") or "",
                "languages": list(languages.keys()),
                "recent_commits": commits_count,
                "url": repo.get("html_url", ""),
            }
        )
    return insights


def _fetch_languages(username: str, repo: str, headers: Dict[str, str]) -> Dict:
    url = f"https://api.github.com/repos/{username}/{repo}/languages"
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code != 200:
        return {}
    return resp.json()


def _fetch_recent_commits_count(username: str, repo: str, headers: Dict[str, str]) -> int:
    url = f"https://api.github.com/repos/{username}/{repo}/commits?per_page=20"
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code != 200:
        return 0
    return len(resp.json())
