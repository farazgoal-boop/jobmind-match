# JobMind Match

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

JobMind Match is a personal job-matching assistant that helps you:
- Parse your CV (PDF/DOCX)
- Pull evidence from your GitHub repos
- Fetch jobs from free public sources
- Rank jobs using TF-IDF + cosine similarity + skill boosting
- Send daily digest via email (optional Telegram-ready output)

## Live Project Showcase

### What this app solves
- Turns your CV + GitHub profile into smart job matches.
- Helps you track your pipeline (saved, applied, replied, interview, rejected).
- Provides assisted apply links for LinkedIn, Upwork, Fiverr, and Google Jobs.

### Add your visual proof (recommended)
- Screenshot path: `docs/assets/dashboard.png`
- Demo GIF path: `docs/assets/demo.gif`

When you add files, use this section:

```markdown
![Dashboard Screenshot](docs/assets/dashboard.png)

![Demo Walkthrough](docs/assets/demo.gif)
```

### Record a quick demo GIF (2 minutes)
1. Open dashboard.
2. Create/select profile.
3. Upload CV.
4. Run matching with filters.
5. Save one job to tracker and update status.
6. Export to GIF and place at `docs/assets/demo.gif`.

## 1) What You Need (Requirements)

### Accounts
- GitHub account (already available)
- At least 1 public email account (for digest)
- Optional Telegram bot token/chat ID

### Skills/Inputs from your side
- Updated CV in PDF or DOCX
- Correct skills list (example: `Python,Django,FastAPI,SQL,Docker`)
- GitHub username with active repos
- Preferred job filters (remote/on-site, countries, salary range)

### Technical requirements
- Python 3.11+
- Git
- VS Code
- Optional Docker Desktop

## 2) Current Folder Structure

```text
JobMind Match/
  app/
    main.py
    config.py
    db.py
    models.py
    schemas.py
    routes/
      __init__.py
      profile.py
      jobs.py
      applications.py
      web.py
    scheduler.py
    static/
      styles.css
      app.js
    templates/
      dashboard.html
    services/
      cv_parser.py
      github_client.py
      matcher.py
      notifier.py
      quota.py
      source_registry.py
      assisted_apply.py
      job_sources/
        __init__.py
        arbeitnow.py
        remotive.py
        weworkremotely.py
  Procfile
  railway.json
  render.yaml
  .env.example
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
```

## 3) Feature Blueprint (Mapped to your DeepSeek prompt)

### A. CV Upload + Parse
- Endpoint: `POST /profile/{candidate_id}/upload-cv`
- Supports `.pdf` and `.docx`
- Extracts text, sections (`experience`, `education`, `projects`) and technologies

### B. GitHub Insights
- Endpoint: `GET /profile/{candidate_id}/github`
- Reads:
  - latest repos
  - repo languages
  - recent commits count

### C. Job Sources (Free-first)
- Implemented sources:
  - Remotive API
  - WeWorkRemotely RSS
  - Arbeitnow API
- Extendable for:
  - WeWorkRemotely RSS or HTML scrape
  - Indeed public pages (careful with robots/ToS)
  - Upwork public opportunities (if officially available endpoint/feed)

### D. Matching Engine
- `app/services/matcher.py`
- Uses:
  - TF-IDF vectorizer
  - cosine similarity
  - manual boost for important skills (`python`, `django`, `fastapi`, ...)

### E. Output Channels
- Dashboard/API responses (FastAPI)
- Email digest (`send_email_digest`)
- Telegram formatter ready (`format_telegram_digest`)
- Web dashboard route: `/dashboard`
- Application Tracker API route: `/applications`
- Assisted apply links for LinkedIn, Upwork, Fiverr, and Google Jobs

## 4) Freemium Without Forced Payment

### Free tier (default)
- 50 matches/month
- 2 sources max (example: Remotive + WeWorkRemotely)
- Daily digest only

### Premium via self-hosting / BYO keys
- Unlimited sources
- Real-time alerts
- Optional LLM explanations (Gemini free tier key from user)

No forced payment is required by this architecture.

## 5) Run Locally (VS Code)

### Option A: Python directly
1. Create virtual environment
2. Install dependencies
3. Copy `.env.example` to `.env`
4. Run server

Commands:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open: `http://127.0.0.1:8000/docs`

### Option B: Docker

```bash
docker compose up --build
```

## 6) API Quick Start

1. Create profile: `POST /profile/`
2. Upload CV: `POST /profile/{id}/upload-cv`
3. GitHub summary: `GET /profile/{id}/github`
4. Browse source jobs: `GET /jobs/sources?sources=remotive,weworkremotely`
5. Get matches with quota tracking: `GET /jobs/match/{id}?top_k=5&sources=remotive,weworkremotely`

## 7) Dashboard Quick Start

- Open: `http://127.0.0.1:8000/dashboard`
- Create profile from form
- Upload CV
- Run matching and open apply page from result cards
- Save matched jobs into tracker and update status: `saved`, `applied`, `interview`, `rejected`
- Use assisted links to search the same role on LinkedIn/Upwork/Fiverr

## 8) Add a New Job Source (No Payment)

Create file: `app/services/job_sources/weworkremotely.py`

Template:

```python
from typing import Dict, List
import requests
from bs4 import BeautifulSoup


def fetch_weworkremotely_jobs(limit: int = 50) -> List[Dict]:
    url = "https://weworkremotely.com/remote-jobs.rss"
    # Parse RSS/XML and return normalized list in the same structure
    return [
        {
            "source": "weworkremotely",
            "title": "...",
            "company": "...",
            "location": "Remote",
            "url": "...",
            "description": "...",
        }
    ]
```

Then combine inside `app/routes/jobs.py` and pass merged jobs to `rank_jobs(...)`.

## 9) Render / Railway / PythonAnywhere (Free-friendly)

### Render.com
- New Web Service from GitHub repo
- Use included file: `render.yaml`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add env vars from `.env.example`

### Railway.app
- Deploy from GitHub
- Uses included `railway.json`
- Start command can use `Procfile` default
- Configure env vars

### PythonAnywhere
- Upload code/repo
- Create virtualenv and install requirements
- Configure web app WSGI/ASGI (FastAPI via Uvicorn or gunicorn+uvicorn worker)

## 10) Your IDs (LinkedIn/Fiverr/Upwork) - Important Note
- LinkedIn/Fiverr/Upwork mostly do not provide open free APIs for full automated applying.
- Safe approach:
  - use public feeds/boards where allowed
  - scrape only where ToS permits
  - use "semi-automatic apply" (show best jobs + open apply page)

## 11) Recommended Next Build Steps

1. Add user authentication (simple email/password or magic link)
2. Add application tracking board (saved/applied/interview/rejected)
3. Add smarter filters (country, salary, contract type)
4. Add optional Gemini summary: "Why this job matches you"
5. Add auto-generated cover-letter drafts

---

Current build already includes multi-source fetching, free-tier limiter, daily scheduler, and a dashboard UI.

## License

MIT
