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


def build_live_search_links(
    search_mode: str,
    offer_type: str,
    client_type: str,
    demand_level: str,
    contact_goal: str,
    counterparty_type: str,
    posted_within: str,
    verified_payment_only: bool,
    trust_signal: str,
    company_size: str,
    proposal_pressure: str,
    platform_targets: list[str],
    search_focus: str,
    region_preference: str,
    remote_only: bool,
    junior_only: bool,
    backend_only: bool,
    pakistan_friendly_only: bool,
    salary_only: bool,
    visa_support_only: bool,
    candidate_skills: str = "",
    custom_keywords: str = "",
) -> list[dict[str, str]]:
    query_text = _compose_live_search_query(
        search_mode=search_mode,
        offer_type=offer_type,
        client_type=client_type,
        demand_level=demand_level,
        counterparty_type=counterparty_type,
        posted_within=posted_within,
        verified_payment_only=verified_payment_only,
        trust_signal=trust_signal,
        company_size=company_size,
        proposal_pressure=proposal_pressure,
        search_focus=search_focus,
        remote_only=remote_only,
        junior_only=junior_only,
        backend_only=backend_only,
        pakistan_friendly_only=pakistan_friendly_only,
        salary_only=salary_only,
        visa_support_only=visa_support_only,
        candidate_skills=candidate_skills,
        custom_keywords=custom_keywords,
    )
    encoded_query = quote_plus(query_text)
    encoded_location = quote_plus(_location_hint_for_region(region_preference))

    catalog = {
        "indeed": {
            "platform": "Indeed",
            "caption": "Newest public listings",
            "url": f"https://pk.indeed.com/jobs?q={encoded_query}&l={encoded_location}&sort=date{_indeed_date_param(posted_within)}",
        },
        "upwork": {
            "platform": "Upwork",
            "caption": "Latest freelance demand",
            "url": f"https://www.upwork.com/nx/search/jobs/?q={encoded_query}&sort=recency{_upwork_payment_param(verified_payment_only)}",
        },
        "fiverr": {
            "platform": "Fiverr",
            "caption": "Direct gig demand",
            "url": f"https://www.fiverr.com/search/gigs?query={encoded_query}",
        },
        "linkedin": {
            "platform": "LinkedIn",
            "caption": "Company and job search",
            "url": _linkedin_url(search_mode, encoded_query, encoded_location, posted_within),
        },
        "google_clients": {
            "platform": "Google Clients",
            "caption": _google_clients_caption(contact_goal),
            "url": f"https://www.google.com/search?q={encoded_query}+{quote_plus(contact_goal)}+client+contact+{encoded_location}",
        },
        "google_maps": {
            "platform": "Google Maps",
            "caption": "Nearby businesses and buyers",
            "url": f"https://www.google.com/maps/search/{encoded_query}+{encoded_location}",
        },
    }

    selected_targets = platform_targets or ["indeed", "linkedin", "upwork", "google_clients"]
    return [catalog[target] for target in selected_targets if target in catalog]


def build_client_access_links(
    search_mode: str,
    offer_type: str,
    client_type: str,
    counterparty_type: str,
    region_preference: str,
    contact_goal: str,
    posted_within: str,
    verified_payment_only: bool,
    trust_signal: str,
    company_size: str,
    custom_keywords: str = "",
) -> list[dict[str, str]]:
    base_terms = [
        offer_type.replace("_", " "),
        client_type.replace("_", " "),
        _counterparty_label(counterparty_type),
        _posted_within_label(posted_within),
        "verified buyer" if verified_payment_only else "",
        _trust_signal_label(trust_signal),
        _company_size_label(company_size),
        custom_keywords.strip(),
    ]
    query_text = " ".join(term for term in base_terms if term)
    encoded_query = quote_plus(query_text or "software services client")
    encoded_location = quote_plus(_location_hint_for_region(region_preference))

    access_links = [
        {
            "platform": "LinkedIn",
            "caption": "Reach target companies",
            "url": f"https://www.linkedin.com/search/results/companies/?keywords={encoded_query}&origin=GLOBAL_SEARCH_HEADER",
        },
        {
            "platform": "Upwork Clients",
            "caption": "Open freelance buyer demand",
            "url": f"https://www.upwork.com/nx/search/jobs/?q={encoded_query}&sort=recency{_upwork_payment_param(verified_payment_only)}",
        },
        {
            "platform": "Fiverr",
            "caption": "Check live gig demand",
            "url": f"https://www.fiverr.com/search/gigs?query={encoded_query}",
        },
        {
            "platform": "Google Prospecting",
            "caption": "Open websites and contacts",
            "url": f"https://www.google.com/search?q={encoded_query}+email+phone+website+{encoded_location}",
        },
        {
            "platform": "Maps Decision Makers",
            "caption": "Local businesses and parties",
            "url": f"https://www.google.com/maps/search/{encoded_query}+{encoded_location}",
        },
    ]

    if search_mode == "job_search":
        return access_links[:2]
    if contact_goal == "meeting":
        access_links.append(
            {
                "platform": "Google Meeting Leads",
                "caption": "Find founders and managers",
                "url": f"https://www.google.com/search?q={encoded_query}+founder+manager+meeting+{encoded_location}",
            }
        )
    return access_links


def build_sales_outreach_links(
    full_name: str,
    email: str,
    offer_type: str,
    product_name: str = "",
    product_url: str = "",
    resume_url: str = "",
    portfolio_url: str = "",
    sales_pitch: str = "",
) -> list[dict[str, str]]:
    offer_label = product_name or offer_type.replace("_", " ").title()
    body_lines = [
        "Hello,",
        "",
        sales_pitch or f"I would like to introduce my {offer_label} and explore if it can help your business.",
        "",
        f"Name: {full_name}",
    ]
    if email:
        body_lines.append(f"Email: {email}")
    if resume_url:
        body_lines.append(f"Resume: {resume_url}")
    if portfolio_url:
        body_lines.append(f"Portfolio: {portfolio_url}")
    if product_url:
        body_lines.append(f"Product: {product_url}")
    body_lines.extend(["", "If relevant, I can share pricing, samples, and a short demo."])

    subject = quote_plus(f"Quick intro: {offer_label}")
    body = quote_plus("\n".join(body_lines))
    whatsapp_text = quote_plus(" ".join(line for line in body_lines if line))

    links = [
        {
            "platform": "Pitch Email",
            "caption": "Send semi-auto email",
            "url": f"mailto:?subject={subject}&body={body}",
        },
        {
            "platform": "WhatsApp Pitch",
            "caption": "Send prefilled WhatsApp pitch",
            "url": f"https://wa.me/?text={whatsapp_text}",
        },
    ]
    if resume_url:
        links.append({"platform": "Resume", "caption": "Open resume", "url": resume_url})
    if portfolio_url:
        links.append({"platform": "Portfolio", "caption": "Open portfolio", "url": portfolio_url})
    if product_url:
        links.append({"platform": "Product", "caption": "Open product page", "url": product_url})
    return links


def _compose_live_search_query(
    search_mode: str,
    offer_type: str,
    client_type: str,
    demand_level: str,
    counterparty_type: str,
    posted_within: str,
    verified_payment_only: bool,
    trust_signal: str,
    company_size: str,
    proposal_pressure: str,
    search_focus: str,
    remote_only: bool,
    junior_only: bool,
    backend_only: bool,
    pakistan_friendly_only: bool,
    salary_only: bool,
    visa_support_only: bool,
    candidate_skills: str,
    custom_keywords: str,
) -> str:
    tokens: list[str] = []

    mode_map = {
        "job_search": "job opening",
        "sell_services": "hire freelancer",
        "sell_products": "buy product supplier",
        "direct_clients": "client requirement",
    }
    tokens.append(mode_map.get(search_mode, "job opening"))

    offer_map = {
        "services": "services",
        "products": "products",
        "software": "software development",
        "design": "design service",
        "marketing": "marketing service",
        "automation": "automation solution",
    }
    tokens.append(offer_map.get(offer_type, offer_type.replace("_", " ")))
    tokens.append(client_type.replace("_", " "))
    tokens.append(_counterparty_label(counterparty_type))
    tokens.append(_trust_signal_label(trust_signal))
    tokens.append(_company_size_label(company_size))
    tokens.append(_proposal_pressure_label(proposal_pressure))

    demand_map = {
        "latest": "latest",
        "urgent": "urgent",
        "budget": "budget",
        "premium": "premium",
        "long_term": "long term",
    }
    tokens.append(demand_map.get(demand_level, demand_level.replace("_", " ")))
    posted_label = _posted_within_label(posted_within)
    if posted_label:
        tokens.append(posted_label)

    focus_map = {
        "python": "Python developer",
        "fastapi": "FastAPI backend developer",
        "flask": "Flask backend developer",
        "fullstack": "full stack developer",
        "all": "software developer",
    }
    tokens.append(focus_map.get(search_focus, "software developer"))

    if backend_only and "backend" not in tokens[0].lower():
        tokens.append("backend")
    if junior_only:
        tokens.append("junior")
    if remote_only:
        tokens.append("remote")
    if pakistan_friendly_only:
        tokens.append("Pakistan friendly")
    if salary_only:
        tokens.append("salary")
    if visa_support_only:
        tokens.append("visa sponsorship")
    if verified_payment_only:
        tokens.append("verified payment")

    skill_tokens = [skill.strip() for skill in candidate_skills.split(",") if skill.strip()]
    tokens.extend(skill_tokens[:2])
    if custom_keywords.strip():
        tokens.append(custom_keywords.strip())

    return " ".join(dict.fromkeys(tokens))


def _location_hint_for_region(region_preference: str) -> str:
    region_map = {
        "pakistan": "Pakistan",
        "global": "Remote",
        "asia": "Asia Remote",
        "europe": "Europe Remote",
        "americas": "Americas Remote",
        "any": "Remote",
    }
    return region_map.get(region_preference, "Remote")
def _linkedin_url(search_mode: str, encoded_query: str, encoded_location: str, posted_within: str) -> str:
    if search_mode == "job_search":
        return f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}&sortBy=DD{_linkedin_time_param(posted_within)}"
    return f"https://www.linkedin.com/search/results/companies/?keywords={encoded_query}&origin=GLOBAL_SEARCH_HEADER"


def _google_clients_caption(contact_goal: str) -> str:
    captions = {
        "apply": "Open websites and openings",
        "pitch": "Find buyers and prospects",
        "meeting": "Find founders and managers",
        "email": "Find emails and contact pages",
    }
    return captions.get(contact_goal, "Find prospects")


def _counterparty_label(counterparty_type: str) -> str:
    labels = {
        "any": "",
        "recruiter": "recruiter",
        "direct_client": "direct client",
        "company": "company",
        "founder": "founder",
    }
    return labels.get(counterparty_type, counterparty_type.replace("_", " "))


def _trust_signal_label(trust_signal: str) -> str:
    labels = {
        "any": "",
        "verified_recruiter": "verified recruiter",
        "verified_client": "verified client",
        "verified_company": "verified company",
        "top_rated_buyer": "top rated buyer",
    }
    return labels.get(trust_signal, trust_signal.replace("_", " "))


def _company_size_label(company_size: str) -> str:
    labels = {
        "any": "",
        "solo": "solo business",
        "small_team": "small team",
        "mid_market": "mid market company",
        "enterprise": "enterprise company",
    }
    return labels.get(company_size, company_size.replace("_", " "))


def _proposal_pressure_label(proposal_pressure: str) -> str:
    labels = {
        "any": "",
        "low": "low competition",
        "medium": "medium competition",
        "high": "high competition",
    }
    return labels.get(proposal_pressure, proposal_pressure.replace("_", " "))


def _posted_within_label(posted_within: str) -> str:
    labels = {
        "any": "",
        "1d": "last 24 hours",
        "3d": "last 3 days",
        "7d": "last 7 days",
        "14d": "last 14 days",
        "30d": "last 30 days",
    }
    return labels.get(posted_within, "")


def _indeed_date_param(posted_within: str) -> str:
    mapping = {
        "1d": "&fromage=1",
        "3d": "&fromage=3",
        "7d": "&fromage=7",
        "14d": "&fromage=14",
        "30d": "&fromage=30",
    }
    return mapping.get(posted_within, "")


def _linkedin_time_param(posted_within: str) -> str:
    mapping = {
        "1d": "&f_TPR=r86400",
        "3d": "&f_TPR=r259200",
        "7d": "&f_TPR=r604800",
        "14d": "&f_TPR=r1209600",
        "30d": "&f_TPR=r2592000",
    }
    return mapping.get(posted_within, "")


def _upwork_payment_param(verified_payment_only: bool) -> str:
    return "&payment_verified=1" if verified_payment_only else ""
