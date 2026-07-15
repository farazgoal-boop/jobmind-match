# CLAUDE.md

Guidance for Claude Code (or any future agent) working in this repository.

## What this repo actually contains

There are **two independent applications** in this repo. Don't confuse them.

1. **`app/`** — the real, shipping product: **JobMind Match**. FastAPI + Jinja2 + vanilla JS + SQLite (SQLModel), packaged as a Windows/macOS/Linux desktop app via PyInstaller. This is what all the marketing docs (`README.md`, `PRO_MARKETING_PLAYBOOK.md`) and the desktop installer describe. **This is almost certainly what any "the app" request refers to.**
2. **`mind-manage/`** — a separate, mostly-scaffolded B2B tool (pnpm/Turborepo monorepo: Next.js web app + Express API + Prisma). Different product (website-scanner/outreach/lead-gen for businesses, not job hunting), different stack (Node/TS, no Tailwind), different visual theme (teal/cream, not indigo). It is **not wired into `app/` in any way**. Don't touch it unless a request is specifically about it.

The rest of this file documents `app/`.

## Architecture

Single dashboard, two modes, one JS-driven panel system:

- The UI has a **Job Hunter mode** (`data-nav-mode="job"`) and a **Lead Provider / Sell Services mode** (`data-nav-mode="sell"`), toggled via the header switch (`[data-role="mode-toggle"]`). Screenshots showing "Job Search / Leads / Tracker / Profile" and "Lead Hunter Pro" are the same app in its two modes.
- All panels live in one big template, `app/templates/dashboard.html`, as `<div class="panel" data-panel="..." data-panel-mode="job|sell">` blocks. Sidebar buttons (`[data-nav-panel]` + `[data-nav-mode]`) show/hide panels client-side — there is no client-side router and no per-panel page navigation; `GET /dashboard` renders the whole shell once.
- `app/static/app.js` (~1050 lines) owns: panel switching (`setActivePanel()`), mode switching, theme toggle wiring, form submission (mixed: some AJAX `fetch()`, most plain POST + redirect), PWA install prompt, mobile pull-to-refresh.
- `app/static/styles.css` (~2750 lines) is the single stylesheet. Design tokens live in `:root` (dark, default) with an `html[data-theme="light"] { ... }` override block. Some light-theme overrides are duplicated inline in `dashboard.html`'s `<head>` to avoid a flash of unstyled theme before `styles.css` loads.
- Theme persistence: an inline `<script>` in `<head>` sets `data-theme` on `<html>` from `localStorage['jmm-theme']` **before paint**, so any new theme value must be added there too, not just in the toggle handler.

## Backend

- `app/main.py` — FastAPI app construction, startup/shutdown hooks (`init_db()`, APScheduler start/stop), mounts `/static`, includes routers: `profile`, `jobs`, `applications`, `web`.
- `app/routes/web.py` — **the catch-all router (~2200 lines)**. Almost every dashboard page, form POST, and `/api/*` JSON endpoint lives here, including the entire lead-hunting API (`/api/scrape/*`) and licensing (`/api/license/*`). Check here first before assuming a route doesn't exist.
- `app/routes/{profile,jobs,applications}.py` — smaller, prefixed routers for profile/job/application CRUD.
- `app/models.py` — SQLModel tables: `CandidateProfile`, `JobListing`, `MatchScore`, `UsageCounter`, `ApplicationRecord`, `ClientLead`, `FilterPreset`, `HuntedContact` (permanent email/WhatsApp dedup registry), `AppSetting` (generic key/value store — also used for license state, there is no separate `License` table).
- `app/db.py` — engine setup + `init_db()`. **Migrations are manual**: `_ensure_candidate_profile_columns()` does raw `ALTER TABLE` to add columns that were added to `CandidateProfile` after initial release. Any new column added to an existing table needs the same treatment (SQLite `CREATE TABLE` won't auto-add columns to existing DBs).
- `app/services/` — one module per concern: `lead_hunter_engine.py` + `lead_hunter_registry.py` + `lead_platforms.py` (200+ lead-source platforms, dedup against `HuntedContact`), `matcher.py` (TF-IDF/cosine job matching), `cv_parser.py`, `github_client.py`, `job_sources/` (per-source job fetchers), `assisted_apply.py`, `notifier.py` (email digest), `quota.py`, `source_registry.py`, `license_service.py`. `app/scheduler.py` runs the daily digest via APScheduler.
- `app/config.py` — `Settings` (plain pydantic `BaseModel`, not `BaseSettings`), loaded from `.env` via `python-dotenv`. `app/paths.py` resolves `app_root()`/`static_dir()`/`templates_dir()`, overridable via `JOBMIND_APP_ROOT` (set by the desktop launcher).

## Data locations

- Dev: `./jobmind.db`, `./.env` at repo root.
- Desktop (PyInstaller) build: `desktop_launcher.py` redirects everything to `~/.jobmind-match/` (DB + `.env`), sets `JOBMIND_APP_ROOT`/`APP_ENV=desktop`, starts Uvicorn, opens the OS default browser (no embedded webview).
- Android: `JOBMIND_DATA_DIR` env var used instead.

## Running it

- Dev server: `uvicorn app.main:app --reload` (or `docker-compose up`, which runs the same command in a container on port 8000).
- Desktop build: `jobmind.spec` (PyInstaller) → `installer/jobmind-match.iss` (Inno Setup, Windows). See `scripts/` for build/packaging helpers (desktop exe, Android APK, icon generation).
- Deploy targets: Render (`render.yaml`) and Railway (`railway.json`, `Procfile`) both just run Uvicorn against `requirements.txt`.

## Testing

There is currently **no automated test suite** anywhere in `app/` (no `pytest`, no `tests/` dir — `requirements-dev.txt` only has `pyinstaller`). If you add tests, add `pytest`/`pytest-playwright` to `requirements-dev.txt` and a `tests/` directory at repo root; there's no existing convention to follow yet.

## Releases

Real GitHub releases exist at `farazgoal-boop/jobmind-match` (tags `v1.0.0`–`v1.0.3`, pushed manually — no CI workflow automates this). `installer/jobmind-match.iss` has its own `MyAppVersion` that must be bumped by hand alongside any release tag.
