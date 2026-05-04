from urllib.parse import quote_plus


def build_assisted_links(job_title: str, company: str) -> dict[str, str]:
    query = quote_plus(f"{job_title} {company}")
    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={query}",
        "indeed": f"https://pk.indeed.com/jobs?q={query}",
        "upwork": f"https://www.upwork.com/nx/search/jobs/?q={query}",
        "fiverr": f"https://www.fiverr.com/search/gigs?query={query}",
        "google_jobs": f"https://www.google.com/search?q={query}+jobs",
    }
