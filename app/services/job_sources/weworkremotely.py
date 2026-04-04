from typing import Dict, List
import xml.etree.ElementTree as ET

import requests


def fetch_weworkremotely_jobs(limit: int = 50) -> List[Dict]:
    url = "https://weworkremotely.com/remote-jobs.rss"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    if channel is None:
        return []

    jobs = []
    for item in channel.findall("item")[:limit]:
        title = item.findtext("title", default="")
        link = item.findtext("link", default="")
        description = item.findtext("description", default="")

        parts = [p.strip() for p in title.split(":", 1)]
        company = parts[0] if len(parts) > 1 else "Unknown"
        normalized_title = parts[1] if len(parts) > 1 else title

        jobs.append(
            {
                "source": "weworkremotely",
                "title": normalized_title,
                "company": company,
                "location": "Remote",
                "url": link,
                "description": description,
            }
        )
    return jobs
