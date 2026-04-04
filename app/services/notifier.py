import smtplib
from email.mime.text import MIMEText
from typing import List, Dict

from app.config import settings


def send_email_digest(to_email: str, matches: List[Dict]) -> None:
    if not settings.smtp_host or not settings.smtp_user:
        return

    body_lines = ["Your daily top job matches:", ""]
    for idx, match in enumerate(matches, start=1):
        job = match["job"]
        body_lines.append(f"{idx}. {job['title']} - {job['company']}")
        body_lines.append(f"   Score: {match['score']}")
        body_lines.append(f"   URL: {job['url']}")
        body_lines.append("")

    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = "JobMind Match Daily Digest"
    msg["From"] = settings.smtp_user
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(msg)


def format_telegram_digest(matches: List[Dict]) -> str:
    rows = ["Top Job Matches"]
    for idx, match in enumerate(matches, start=1):
        job = match["job"]
        rows.append(f"{idx}) {job['title']} - {job['company']} ({match['score']})")
        rows.append(job["url"])
    return "\n".join(rows)
