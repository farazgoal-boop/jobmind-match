from urllib.parse import quote_plus


def build_assisted_links(
    job_title: str,
    company: str,
    candidate_name: str = "",
    candidate_email: str = "",
    resume_url: str = "",
    portfolio_url: str = "",
    github_username: str = "",
) -> dict[str, str]:
    query = quote_plus(f"{job_title} {company}")
    subject = quote_plus(f"Application for {job_title} at {company}")
    body_lines = [
        "Hello Hiring Team,",
        "",
        f"I would like to apply for the {job_title} role at {company}.",
    ]

    if candidate_name:
        body_lines.append(f"Name: {candidate_name}")
    if candidate_email:
        body_lines.append(f"Email: {candidate_email}")
    if resume_url:
        body_lines.append(f"Resume: {resume_url}")
    if portfolio_url:
        body_lines.append(f"Portfolio: {portfolio_url}")
    if github_username:
        body_lines.append(f"GitHub: https://github.com/{github_username}")

    body_lines.extend(["", "Thank you."])
    email_body = quote_plus("\n".join(body_lines))

    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={query}",
        "indeed": f"https://pk.indeed.com/jobs?q={query}",
        "upwork": f"https://www.upwork.com/nx/search/jobs/?q={query}",
        "fiverr": f"https://www.fiverr.com/search/gigs?query={query}",
        "google_jobs": f"https://www.google.com/search?q={query}+jobs",
        "email_apply": f"mailto:?subject={subject}&body={email_body}",
    }
