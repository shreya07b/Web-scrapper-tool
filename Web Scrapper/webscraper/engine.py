from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from webscraper.extractors import extract_items
from webscraper.models import LogRecord, RuleDefinition, ScrapedRecord, ScraperType, SiteRule
from webscraper.pagination import PaginationHandler
from webscraper.reliability import SessionFactory

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    async_playwright = None


@dataclass
class EngineResult:
    records: list[ScrapedRecord]
    logs: list[LogRecord]


class ScraperEngine:
    def __init__(self) -> None:
        self.pagination_handler = PaginationHandler()

    async def run(self, job_id: str, rule_definition: RuleDefinition) -> EngineResult:
        rule = rule_definition.rule
        if rule.scraper_type == ScraperType.dynamic:
            return await self._run_dynamic(job_id, rule)
        if rule.scraper_type == ScraperType.auto:
            try:
                return await self._run_static(job_id, rule)
            except Exception as exc:
                fallback_logs = [LogRecord(job_id=job_id, event_type="fallback", message=str(exc))]
                dynamic_result = await self._run_dynamic(job_id, rule)
                dynamic_result.logs = fallback_logs + dynamic_result.logs
                return dynamic_result
        return await self._run_static(job_id, rule)

    async def _run_static(self, job_id: str, rule: SiteRule) -> EngineResult:
        session_factory = SessionFactory(rule.anti_block)
        session = session_factory.build_session(self._merged_headers(rule))
        visited_urls: set[str] = set()
        pending_urls = [str(url) for url in rule.start_urls]
        records: list[ScrapedRecord] = []
        logs: list[LogRecord] = []
        page_number = 1

        while pending_urls:
            url = pending_urls.pop(0)
            if url in visited_urls:
                continue
            visited_urls.add(url)
            response = session_factory.get(session, url, timeout=rule.anti_block.timeout_seconds)
            logs.append(LogRecord(job_id=job_id, event_type="page_fetched", message=url))
            extracted = extract_items(response.text, url, rule)
            for item in extracted:
                records.append(
                    ScrapedRecord(
                        job_id=job_id,
                        source_url=url,
                        extracted_json=normalize_record(item),
                    )
                )
            next_urls = self.pagination_handler.build_next_urls(url, response.text, rule, page_number)
            pending_urls.extend(next_url for next_url in next_urls if next_url not in visited_urls)
            page_number += 1

        return EngineResult(records=records, logs=logs)

    async def _run_dynamic(self, job_id: str, rule: SiteRule) -> EngineResult:
        if async_playwright is None:
            raise RuntimeError("Dynamic scraping requires the optional Playwright dependency.")
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                page = await browser.new_page(extra_http_headers=self._merged_headers(rule))
                await page.goto(str(rule.start_urls[0]), wait_until="networkidle")
                if rule.wait_for_selector:
                    await page.wait_for_selector(
                        rule.wait_for_selector,
                        timeout=rule.anti_block.timeout_seconds * 1000,
                    )
                html = await page.content()
                await browser.close()
        except Exception as exc:
            raise RuntimeError(
                "Dynamic scraping requires Playwright and browser binaries. "
                f"Original error: {exc}"
            ) from exc

        records = [
            ScrapedRecord(
                job_id=job_id,
                source_url=str(rule.start_urls[0]),
                extracted_json=normalize_record(item),
            )
            for item in extract_items(html, str(rule.start_urls[0]), rule)
        ]
        logs = [
            LogRecord(
                job_id=job_id,
                event_type="dynamic_page_rendered",
                message=str(rule.start_urls[0]),
            )
        ]
        return EngineResult(records=records, logs=logs)

    def _merged_headers(self, rule: SiteRule) -> dict[str, str]:
        headers = dict(rule.headers)
        if rule.authentication:
            headers.update(rule.authentication.headers)
            if rule.authentication.token_env:
                token = os.getenv(rule.authentication.token_env)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
        return headers


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, str):
            normalized[key] = " ".join(value.split())
        else:
            normalized[key] = value
    return normalized
