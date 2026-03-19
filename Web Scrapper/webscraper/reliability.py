from __future__ import annotations

import random
import time
from collections import deque

import requests

from webscraper.models import AntiBlockRule


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
]


class ThrottleController:
    def __init__(self, rate_limit_per_second: float) -> None:
        self.rate_limit_per_second = max(rate_limit_per_second, 0.1)
        self.timestamps: deque[float] = deque(maxlen=4)

    def wait(self) -> None:
        minimum_spacing = 1.0 / self.rate_limit_per_second
        if self.timestamps:
            elapsed = time.monotonic() - self.timestamps[-1]
            if elapsed < minimum_spacing:
                time.sleep(minimum_spacing - elapsed)
        self.timestamps.append(time.monotonic())


class ProxyManager:
    def __init__(self, proxy_urls: list[str]) -> None:
        self.proxy_urls = proxy_urls
        self.index = 0

    def next_proxy(self) -> dict[str, str] | None:
        if not self.proxy_urls:
            return None
        proxy = self.proxy_urls[self.index % len(self.proxy_urls)]
        self.index += 1
        return {"http": proxy, "https": proxy}


class SessionFactory:
    def __init__(self, anti_block: AntiBlockRule) -> None:
        self.anti_block = anti_block
        self.proxy_manager = ProxyManager(anti_block.proxy_urls)
        self.throttle = ThrottleController(anti_block.rate_limit_per_second)

    def build_session(self, headers: dict[str, str]) -> requests.Session:
        session = requests.Session()
        request_headers = dict(headers)
        if self.anti_block.rotate_user_agent:
            request_headers.setdefault("User-Agent", random.choice(USER_AGENTS))
        session.headers.update(request_headers)
        return session

    def get(self, session: requests.Session, url: str, timeout: int) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.anti_block.max_retries + 1):
            try:
                self.throttle.wait()
                proxies = self.proxy_manager.next_proxy()
                response = session.get(url, timeout=timeout, proxies=proxies)
                response.raise_for_status()
                if response.encoding in (None, "ISO-8859-1"):
                    response.encoding = response.apparent_encoding
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.anti_block.max_retries:
                    break
                time.sleep(self.anti_block.backoff_seconds * attempt)
        if last_error is None:
            raise RuntimeError("Unknown request error")
        raise last_error
