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
- Desktop (PyInstaller) build: redirects everything to `~/.jobmind-match/` (DB + `.env`), sets `JOBMIND_APP_ROOT`/`APP_ENV=desktop`, starts Uvicorn — but **which launcher script actually ships differs by platform**, and `jobmind.spec` is misleading here:
  - **Windows** (the real installer users get, via `.github/workflows/build-desktop.yml`'s `build-windows` job → `scripts/build_desktop_exe.bat`): built from `scripts/desktop_launcher.py`, which opens the app in a dedicated **pywebview native window** (WebView2-backed, no browser chrome) and only falls back to an OS-browser window if pywebview/WebView2 itself fails. `jobmind.spec` (which points at the root-level launcher below) is **not used** by this build path at all.
  - **macOS/Linux**, and any manual build actually run via `jobmind.spec`: built from the root-level `desktop_launcher.py`, which starts Uvicorn and opens the OS default browser (no embedded webview) — this is the only launcher `jobmind.spec` references.
  - Verified 2026-08-06 by downloading and running the real v1.0.11 `JobMind-Match-Setup.exe`: the installed `_internal/webview` package and the `jobmind-launcher.log` line "Native window closed by user" only exist in `scripts/desktop_launcher.py`, confirming that's what the Windows build actually bundles.
- Android: `JOBMIND_DATA_DIR` env var used instead.

## Running it

- Dev server: `uvicorn app.main:app --reload` (or `docker-compose up`, which runs the same command in a container on port 8000).
- Desktop build: `jobmind.spec` (PyInstaller) → `installer/jobmind-match.iss` (Inno Setup, Windows). See `scripts/` for build/packaging helpers (desktop exe, Android APK, icon generation).
- Deploy targets: Render (`render.yaml`) and Railway (`railway.json`, `Procfile`) both just run Uvicorn against `requirements.txt`.

## Testing

There **is** a `pytest` suite at repo root `tests/` (43 tests as of this writing). Run it with `pytest` from repo root (config: `pytest.ini`, `testpaths = tests`); deps are in `requirements-dev.txt` (`pytest`, `httpx`).

- `tests/conftest.py` points `DATABASE_URL` at a temp-file SQLite DB (set **before** any `app.*` import — `app/db.py` builds its engine as a module-level singleton at import time, so this must happen first) and calls `init_db()` once per test session (not per-test) — tests share one DB, so use unique data per test (e.g. unique emails) rather than relying on a clean slate.
- Two fixtures: `db_session` (a `Session` on the app's engine) and `fresh_engine` (a brand-new engine pointed at the same DB file, for simulating "the process restarted" — used by the hunt-session-persistence/export-recovery tests).
- Route tests use `with TestClient(app) as client:` — the `with` block matters, it's what fires the real startup/shutdown lifespan (`init_db()`, `start_scheduler()`); `start_scheduler()` only schedules cron/interval jobs, it doesn't run them within a test's lifetime, so this is safe.
- Tests never hit real networks or the real `.env`: job-source fetchers are monkeypatched (see `test_routes_jobs.py`), and `license_service._env_path()` is monkeypatched to a `tmp_path` in `test_license_service.py`.
- Not yet covered: `lead_hunter_engine.py`/`lead_hunter_registry.py`/`website_crawler.py`/`google_places_source.py`/`github_client.py`/`assisted_apply.py`/`notifier.py` beyond what `test_export_and_recovery.py` and `test_hunt_session_persistence.py` already exercise — these do real HTTP/SMTP work and would need mocked-network tests as a follow-up.

## Releases

Real GitHub releases exist at `farazgoal-boop/jobmind-match` (tags `v1.0.0`–`v1.0.3`, pushed manually — no CI workflow automates this). `installer/jobmind-match.iss` has its own `MyAppVersion` that must be bumped by hand alongside any release tag.
