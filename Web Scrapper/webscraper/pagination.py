from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from webscraper.models import PaginationType, SiteRule


class PaginationHandler:
    def build_next_urls(
        self, current_url: str, current_html: str, rule: SiteRule, page_number: int
    ) -> list[str]:
        pagination = rule.pagination
        if pagination.type == PaginationType.none:
            return []
        if page_number >= pagination.max_pages:
            return []
        if pagination.type == PaginationType.next_button:
            return self._handle_next_button(current_url, current_html, pagination.selector)
        if pagination.type == PaginationType.page_param:
            return [self._handle_page_param(current_url, pagination.param_name, page_number + 1)]
        return []

    def _handle_next_button(
        self, current_url: str, current_html: str, selector: str | None
    ) -> list[str]:
        if not selector:
            return []
        soup = BeautifulSoup(current_html, "html.parser")
        element = soup.select_one(selector)
        if element is None:
            return []
        href = element.get("href")
        if not href:
            return []
        return [urljoin(current_url, href)]

    def _handle_page_param(self, current_url: str, param_name: str, next_page: int) -> str:
        parts = urlsplit(current_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query[param_name] = str(next_page)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
