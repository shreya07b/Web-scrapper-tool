from __future__ import annotations

import asyncio
from datetime import datetime

from webscraper.engine import ScraperEngine
from webscraper.exporters import ExportService
from webscraper.models import JobCreateRequest, JobRecord, JobStatus, JobStatusResponse, LogRecord
from webscraper.storage import Storage


class JobManager:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        self.engine = ScraperEngine()
        self.export_service = ExportService()
        self.tasks: dict[str, asyncio.Task] = {}

    async def create_job(self, request: JobCreateRequest) -> JobRecord:
        rule = self.storage.get_rule(request.rule_id)
        job = JobRecord(
            rule_id=request.rule_id,
            target_site=rule.site_name,
            priority=request.priority,
            output_formats=request.output_formats,
        )
        self.storage.create_job(job)
        self.storage.insert_log(
            LogRecord(job_id=job.job_id, event_type="job_created", message="Job created")
        )
        self.tasks[job.job_id] = asyncio.create_task(self._run_job(job.job_id))
        return job

    async def _run_job(self, job_id: str) -> None:
        job = self.storage.get_job(job_id)
        rule = self.storage.get_rule(job.rule_id)
        job.status = JobStatus.running
        job.start_time = datetime.utcnow()
        self.storage.update_job(job)
        self.storage.insert_log(
            LogRecord(job_id=job_id, event_type="job_started", message="Job started")
        )
        try:
            result = await self.engine.run(job_id, rule)
            self.storage.insert_results(result.records)
            for log in result.logs:
                self.storage.insert_log(log)
            self.export_service.export(job_id, result.records, job.output_formats)
            job.status = JobStatus.success
            job.total_records = len(result.records)
        except Exception as exc:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            self.storage.insert_log(
                LogRecord(job_id=job_id, event_type="job_failed", message=str(exc))
            )
        finally:
            job.end_time = datetime.utcnow()
            self.storage.update_job(job)

    def get_job_status(self, job_id: str) -> JobStatusResponse:
        job = self.storage.get_job(job_id)
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            total_records=job.total_records,
            error_message=job.error_message,
        )

    def get_job_results(self, job_id: str):
        return self.storage.get_results(job_id)

    def get_job_logs(self, job_id: str):
        return self.storage.get_logs(job_id)

    async def sleep_briefly(self) -> None:
        await asyncio.sleep(0.5)
