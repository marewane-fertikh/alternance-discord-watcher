"""Base adapter interfaces and HTTP helper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
import logging
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LOGGER = logging.getLogger(__name__)


class SourceAdapter(ABC):
    """Base contract for source adapters."""

    name: str

    @abstractmethod
    def fetch_offers(self) -> list[Any]:
        """Fetch and parse offers from source."""


class SimpleResponse:
    """Small response object for urllib calls."""

    def __init__(self, text: str, status_code: int) -> None:
        self.text = text
        self.status_code = status_code


class HttpFetcher:
    """HTTP fetcher with retries, timeout, and rate limiting."""

    def __init__(self, timeout: float, delay_seconds: float, user_agent: str, retries: int = 3) -> None:
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.user_agent = user_agent
        self.retries = retries

    def get(self, url: str, params: dict[str, str] | None = None) -> SimpleResponse:
        """GET with retry and delay."""

        target = url
        if params:
            target = f"{url}?{urlencode(params)}"
        attempt = 0
        while True:
            try:
                req = Request(target, headers={"User-Agent": self.user_agent})
                with urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                    text = resp.read().decode("utf-8", errors="replace")
                    status_code = getattr(resp, "status", 200)
                time.sleep(self.delay_seconds)
                return SimpleResponse(text, status_code)
            except Exception as exc:  # noqa: BLE001
                attempt += 1
                if attempt >= self.retries:
                    raise
                backoff = 0.5 * attempt
                LOGGER.warning("http_retry", extra={"url": target, "attempt": attempt, "error": str(exc), "backoff": backoff})
                time.sleep(backoff)


def parse_text(node: object | None, default: str = "") -> str:
    """Return stripped text from bs4 node-like object."""

    if node is None:
        return default
    get_text = getattr(node, "get_text", None)
    if callable(get_text):
        return get_text(" ", strip=True)
    return str(node).strip() or default


def safe_iter(items: Iterable[object] | None) -> Iterable[object]:
    """Yield from iterable or empty."""

    return items or []
