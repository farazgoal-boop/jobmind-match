from typing import Dict, List
import requests


def fetch_remotive_jobs(limit: int = 50) -> List[Dict]:
    url = "https://remotive.com/api/remote-jobs"
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    jobs = []
    for item in response.json().get("jobs", [])[:limit]:
        jobs.append(
            {
                "source": "remotive",
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("candidate_required_location", "Remote"),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "salary": item.get("salary", ""),
                "visa_support": False,
            }
        )
    return jobs
