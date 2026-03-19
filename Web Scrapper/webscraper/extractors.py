from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from lxml import html as lxml_html

from webscraper.models import FieldRule, SelectorType, SiteRule


def extract_items(page_html: str, source_url: str, rule: SiteRule) -> list[dict[str, Any]]:
    soup = BeautifulSoup(page_html, "html.parser")
    nodes = soup.select(rule.item_selector)
    if not nodes:
        raise ValueError(f"No items found for selector '{rule.item_selector}'.")

    tree = lxml_html.fromstring(page_html)
    records: list[dict[str, Any]] = []
    for index, node in enumerate(nodes, start=1):
        record: dict[str, Any] = {}
        for field in rule.fields:
            record[field.name] = extract_field_value(node, tree, field, source_url, index)
        records.append(record)
    return records


def extract_field_value(
    node: Tag,
    tree: Any,
    field: FieldRule,
    source_url: str,
    index: int,
) -> Any:
    if field.selector_type == SelectorType.css:
        value = _extract_css(node, field)
    elif field.selector_type == SelectorType.regex:
        value = _extract_regex(str(node), field)
    else:
        value = _extract_xpath(tree, field, index)

    if value in (None, ""):
        if field.required:
            raise ValueError(f"Required field '{field.name}' could not be extracted.")
        return field.default

    if field.attr == "href" and isinstance(value, str):
        return urljoin(source_url, value)
    return value


def _extract_css(node: Tag, field: FieldRule) -> Any:
    element = node.select_one(field.selector)
    if element is None:
        return None
    if field.attr:
        return element.get(field.attr)
    return element.get_text(separator=" ", strip=True)


def _extract_regex(raw_html: str, field: FieldRule) -> Any:
    match = re.search(field.selector, raw_html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return match.group(field.regex_group)


def _extract_xpath(tree: Any, field: FieldRule, index: int) -> Any:
    results = tree.xpath(f"({field.selector})[{index}]")
    if not results:
        return None
    value = results[0]
    if hasattr(value, "text_content"):
        return value.text_content().strip()
    return str(value).strip()
