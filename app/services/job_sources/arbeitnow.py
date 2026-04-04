from typing import Dict, List

import requests


def fetch_arbeitnow_jobs(limit: int = 50) -> List[Dict]:
    url = "https://www.arbeitnow.com/api/job-board-api"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    jobs = []
    for item in resp.json().get("data", [])[:limit]:
        jobs.append(
            {
                "source": "arbeitnow",
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": ", ".join(item.get("location", [])) or "Remote",
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            }
        )
    return jobs
