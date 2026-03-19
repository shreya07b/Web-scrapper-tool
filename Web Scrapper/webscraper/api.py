from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from webscraper.job_manager import JobManager
from webscraper.models import (
    JobCreateRequest,
    JobLaunchRequest,
    RuleCreateRequest,
    ScraperType,
)
from webscraper.storage import Storage


BASE_DIR = Path(__file__).resolve().parent.parent
(BASE_DIR / "exports").mkdir(exist_ok=True)
(BASE_DIR / "webscraper" / "static").mkdir(exist_ok=True)
storage = Storage()
storage.initialize()
job_manager = JobManager(storage)

app = FastAPI(title="Advanced Web Scraper Platform", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "webscraper" / "static"), name="static")
app.mount("/exports", StaticFiles(directory=BASE_DIR / "exports"), name="exports")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Advanced Web Scraper Platform API"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return (BASE_DIR / "webscraper" / "static" / "dashboard.html").read_text(
        encoding="utf-8"
    )


@app.post("/rules/create")
def create_rule(payload: RuleCreateRequest) -> dict[str, str]:
    rule_id = storage.create_rule(payload)
    return {"rule_id": rule_id, "site_name": payload.site_name}


@app.get("/sites/supported")
def list_supported_sites() -> list[dict[str, str]]:
    return storage.list_rules()


@app.post("/jobs/create")
async def create_job(payload: JobCreateRequest) -> dict[str, str]:
    try:
        job = await job_manager.create_job(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"job_id": job.job_id, "status": job.status.value}


@app.post("/jobs/launch")
async def launch_job(payload: JobLaunchRequest) -> dict[str, str]:
    try:
        rule_definition = storage.get_rule(payload.rule_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    updated_rule = rule_definition.model_copy(
        update={
            "rule": rule_definition.rule.model_copy(
                update={
                    "scraper_type": payload.mode,
                    "pagination": rule_definition.rule.pagination.model_copy(
                        update={"max_pages": max(payload.pages, 1)}
                    ),
                }
            )
        }
    )
    runtime_rule_id = storage.create_rule(updated_rule)
    job = await job_manager.create_job(
        JobCreateRequest(
            rule_id=runtime_rule_id,
            priority=payload.priority,
            output_formats=payload.output_formats,
        )
    )
    return {"job_id": job.job_id, "status": job.status.value, "rule_id": runtime_rule_id}


@app.post("/jobs/run/{job_id}")
async def run_job(job_id: str) -> dict[str, str]:
    try:
        status = job_manager.get_job_status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"job_id": status.job_id, "status": status.status.value}


@app.get("/jobs/status/{job_id}")
def get_job_status(job_id: str):
    try:
        return job_manager.get_job_status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/jobs")
def list_jobs(limit: int = 25):
    jobs = storage.list_jobs(limit=limit)
    return [
        {
            "job_id": job.job_id,
            "rule_id": job.rule_id,
            "target_site": job.target_site,
            "status": job.status.value,
            "priority": job.priority,
            "total_records": job.total_records,
            "error_message": job.error_message,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "progress": _job_progress(job.status.value),
            "exports": {
                "csv": f"/exports/{job.job_id}.csv",
                "json": f"/exports/{job.job_id}.json",
                "xlsx": f"/exports/{job.job_id}.xlsx",
            },
        }
        for job in jobs
    ]


@app.get("/jobs/results/{job_id}")
def get_job_results(job_id: str):
    try:
        return job_manager.get_job_results(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/jobs/logs/{job_id}")
def get_job_logs(job_id: str):
    try:
        return job_manager.get_job_logs(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/dashboard/summary")
def get_dashboard_summary():
    return {
        "summary": storage.get_dashboard_summary(),
        "jobs": list_jobs(limit=12),
        "rules": storage.list_rules(),
    }


def _job_progress(status: str) -> int:
    if status == "success":
        return 100
    if status == "running":
        return 60
    if status == "retrying":
        return 40
    if status == "pending":
        return 15
    return 100 if status == "cancelled" else 0
