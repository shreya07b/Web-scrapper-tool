from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    retrying = "retrying"
    cancelled = "cancelled"


class ScraperType(str, Enum):
    static = "static"
    dynamic = "dynamic"
    auto = "auto"


class SelectorType(str, Enum):
    css = "css"
    regex = "regex"
    xpath = "xpath"


class PaginationType(str, Enum):
    none = "none"
    next_button = "next_button"
    page_param = "page_param"
    load_more = "load_more"
    infinite_scroll = "infinite_scroll"


class FieldRule(BaseModel):
    name: str
    selector: str
    selector_type: SelectorType = SelectorType.css
    attr: str | None = None
    regex_group: int = 1
    required: bool = False
    default: str | None = None


class PaginationRule(BaseModel):
    type: PaginationType = PaginationType.none
    selector: str | None = None
    param_name: str = "page"
    start_page: int = 1
    max_pages: int = 1


class AuthRule(BaseModel):
    login_url: HttpUrl | None = None
    username_env: str | None = None
    password_env: str | None = None
    token_env: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class AntiBlockRule(BaseModel):
    max_retries: int = 3
    backoff_seconds: float = 1.5
    rate_limit_per_second: float = 1.0
    proxy_urls: list[str] = Field(default_factory=list)
    rotate_user_agent: bool = True
    timeout_seconds: int = 20


class SiteRule(BaseModel):
    site_name: str
    start_urls: list[HttpUrl]
    scraper_type: ScraperType = ScraperType.auto
    item_selector: str
    wait_for_selector: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    pagination: PaginationRule = Field(default_factory=PaginationRule)
    authentication: AuthRule | None = None
    anti_block: AntiBlockRule = Field(default_factory=AntiBlockRule)
    fields: list[FieldRule]


class RuleDefinition(BaseModel):
    site_name: str
    rule: SiteRule


class JobCreateRequest(BaseModel):
    rule_id: str
    priority: int = 5
    output_formats: list[Literal["json", "csv", "xlsx"]] = Field(
        default_factory=lambda: ["json"]
    )


class JobLaunchRequest(BaseModel):
    rule_id: str
    mode: ScraperType = ScraperType.static
    pages: int = 1
    priority: int = 5
    output_formats: list[Literal["json", "csv", "xlsx"]] = Field(
        default_factory=lambda: ["json", "csv", "xlsx"]
    )


class JobRecord(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    rule_id: str
    target_site: str
    status: JobStatus = JobStatus.pending
    priority: int = 5
    output_formats: list[str] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_records: int = 0
    error_message: str | None = None


class ScrapedRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    source_url: str
    extracted_json: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LogRecord(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    event_type: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_records: int
    error_message: str | None = None


class RuleCreateRequest(BaseModel):
    site_name: str
    rule: SiteRule


class DashboardSummary(BaseModel):
    total_jobs: int
    active_jobs: int
    success_rate: float
    records_scraped: int
    active_job_ids: list[str]
