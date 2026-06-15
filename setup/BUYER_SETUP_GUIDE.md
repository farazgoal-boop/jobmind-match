# JobMind Match Premium — Buyer Setup Guide ($79 Lifetime)

Thank you for purchasing JobMind Match on Gumroad.

## What You Get

- **Job Search Mode** — CV matching, job boards, application tracker
- **Sell Services Mode** — Lead Hunter Pro (212+ platforms), client search, lead CRM
- **Permanent dedup** — hunted emails & WhatsApp numbers are saved forever; never searched again
- **Bundled Python** — no python.org install required (Windows installer)
- **Lifetime license** — 1 PC, activate with your Gumroad key on first launch

---

## Windows Install (Recommended)

1. Run **`JobMind-Match-Setup.exe`** from your Gumroad download
2. Complete the setup wizard (about 1–2 minutes first time)
3. App opens automatically — enter your **Gumroad license key**
4. Use **Start Menu → JobMind Match Premium** daily

**To close:** Start Menu → Quit JobMind Match

---

## Lead Hunter Pro

1. Switch to **Sell Services** mode (header toggle)
2. Open **Lead Hunter** → choose platform chips → **Start Hunting**
3. The app scans **212+ sources** (GitHub, Reddit, Dev.to, RSS boards, marketplaces, etc.)
4. Every email/WhatsApp found is stored in your local database — **never hunted twice**
5. Export as CSV, XLS, JSON, TXT, or HTML

---

## Optional: ZIP / Developer Setup

If you received a ZIP instead of the installer:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open: `http://127.0.0.1:8000/dashboard`

---

## Optional Configuration (.env)

| Variable | Purpose |
|----------|---------|
| `LICENSE_KEY` | Pre-fill Gumroad license (optional) |
| `GITHUB_TOKEN` | Higher GitHub API rate limits for Lead Hunter |
| `SMTP_HOST/USER/PASS` | Daily email digest |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 in use | Quit JobMind Match from Start Menu, then relaunch |
| License modal | Use key from Gumroad purchase email |
| Lead Hunter returns 0 | Check internet; try GitHub + Reddit chips first |
| Re-hunting same email | Should not happen — check **Saved (Never Re-hunt)** stat |

---

## Support

Reply to your Gumroad receipt with your issue and a screenshot.

---

## License

Lifetime use on **one computer**. See `setup/LICENSE.txt`.
