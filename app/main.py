import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routes import applications, jobs, profile, web
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    try:
        init_db()
        start_scheduler()
    except Exception:
        logger.exception("Application startup failed")
        raise


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=302)


app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(web.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
