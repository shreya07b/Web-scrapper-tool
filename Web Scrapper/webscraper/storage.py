from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from webscraper.models import JobRecord, JobStatus, LogRecord, RuleDefinition, ScrapedRecord


class Storage:
    def __init__(self, db_path: str = "scraper.db") -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rules (
                    rule_id TEXT PRIMARY KEY,
                    site_name TEXT NOT NULL,
                    rule_json TEXT NOT NULL,
                    active_flag INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    target_site TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    output_formats TEXT NOT NULL,
                    start_time TEXT NULL,
                    end_time TEXT NULL,
                    total_records INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT NULL
                );
                CREATE TABLE IF NOT EXISTS scraped_data (
                    record_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    extracted_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                """
            )

    def create_rule(self, rule: RuleDefinition) -> str:
        rule_id = f"{rule.site_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO rules (rule_id, site_name, rule_json, active_flag, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (rule_id, rule.site_name, rule.model_dump_json(), datetime.utcnow().isoformat()),
            )
        return rule_id

    def get_rule(self, rule_id: str) -> RuleDefinition:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT rule_json FROM rules WHERE rule_id = ?",
                (rule_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Rule {rule_id} was not found.")
        return RuleDefinition.model_validate_json(row["rule_json"])

    def list_rules(self) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT rule_id, site_name FROM rules WHERE active_flag = 1 ORDER BY created_at DESC"
            ).fetchall()
        return [{"rule_id": row["rule_id"], "site_name": row["site_name"]} for row in rows]

    def create_job(self, job: JobRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, rule_id, target_site, status, priority, output_formats,
                    start_time, end_time, total_records, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.rule_id,
                    job.target_site,
                    job.status.value,
                    job.priority,
                    json.dumps(job.output_formats),
                    self._dt(job.start_time),
                    self._dt(job.end_time),
                    job.total_records,
                    job.error_message,
                ),
            )

    def update_job(self, job: JobRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, start_time = ?, end_time = ?, total_records = ?, error_message = ?
                WHERE job_id = ?
                """,
                (
                    job.status.value,
                    self._dt(job.start_time),
                    self._dt(job.end_time),
                    job.total_records,
                    job.error_message,
                    job.job_id,
                ),
            )

    def get_job(self, job_id: str) -> JobRecord:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Job {job_id} was not found.")
        return JobRecord(
            job_id=row["job_id"],
            rule_id=row["rule_id"],
            target_site=row["target_site"],
            status=JobStatus(row["status"]),
            priority=row["priority"],
            output_formats=json.loads(row["output_formats"]),
            start_time=self._parse_dt(row["start_time"]),
            end_time=self._parse_dt(row["end_time"]),
            total_records=row["total_records"],
            error_message=row["error_message"],
        )

    def list_jobs(self, limit: int = 25) -> list[JobRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY COALESCE(start_time, end_time) DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            JobRecord(
                job_id=row["job_id"],
                rule_id=row["rule_id"],
                target_site=row["target_site"],
                status=JobStatus(row["status"]),
                priority=row["priority"],
                output_formats=json.loads(row["output_formats"]),
                start_time=self._parse_dt(row["start_time"]),
                end_time=self._parse_dt(row["end_time"]),
                total_records=row["total_records"],
                error_message=row["error_message"],
            )
            for row in rows
        ]

    def get_dashboard_summary(self) -> dict[str, object]:
        with self.connect() as connection:
            total_jobs = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            active_rows = connection.execute(
                "SELECT job_id FROM jobs WHERE status IN (?, ?, ?)",
                (JobStatus.pending.value, JobStatus.running.value, JobStatus.retrying.value),
            ).fetchall()
            success_jobs = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = ?",
                (JobStatus.success.value,),
            ).fetchone()[0]
            finished_jobs = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN (?, ?)",
                (JobStatus.success.value, JobStatus.failed.value),
            ).fetchone()[0]
            records_scraped = connection.execute(
                "SELECT COALESCE(SUM(total_records), 0) FROM jobs"
            ).fetchone()[0]

        success_rate = 0.0
        if finished_jobs:
            success_rate = round((success_jobs / finished_jobs) * 100, 1)

        return {
            "total_jobs": total_jobs,
            "active_jobs": len(active_rows),
            "success_rate": success_rate,
            "records_scraped": int(records_scraped or 0),
            "active_job_ids": [row["job_id"] for row in active_rows],
        }

    def insert_results(self, records: list[ScrapedRecord]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO scraped_data (record_id, job_id, source_url, extracted_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.record_id,
                        record.job_id,
                        record.source_url,
                        json.dumps(record.extracted_json),
                        record.created_at.isoformat(),
                    )
                    for record in records
                ],
            )

    def get_results(self, job_id: str) -> list[ScrapedRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM scraped_data WHERE job_id = ? ORDER BY created_at ASC",
                (job_id,),
            ).fetchall()
        return [
            ScrapedRecord(
                record_id=row["record_id"],
                job_id=row["job_id"],
                source_url=row["source_url"],
                extracted_json=json.loads(row["extracted_json"]),
                created_at=self._parse_dt(row["created_at"]) or datetime.utcnow(),
            )
            for row in rows
        ]

    def insert_log(self, log: LogRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO logs (log_id, job_id, event_type, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (log.log_id, log.job_id, log.event_type, log.message, log.timestamp.isoformat()),
            )

    def get_logs(self, job_id: str) -> list[LogRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM logs WHERE job_id = ? ORDER BY timestamp ASC",
                (job_id,),
            ).fetchall()
        return [
            LogRecord(
                log_id=row["log_id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                message=row["message"],
                timestamp=self._parse_dt(row["timestamp"]) or datetime.utcnow(),
            )
            for row in rows
        ]

    @staticmethod
    def _dt(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None
