"""Welcome to the Jungle adapter implementation."""

from __future__ import annotations

from datetime import datetime
import html
import json
import logging
import re
from urllib.parse import urljoin

from watcher.adapters.base import HttpFetcher, SourceAdapter
from watcher.domain.models import Offer


LOGGER = logging.getLogger(__name__)


class WelcomeToTheJungleAdapter(SourceAdapter):
    """Fetch apprenticeship offers from WTTJ public search results."""

    name = "welcome_to_the_jungle"
    BASE_URL = "https://www.welcometothejungle.com/fr/jobs"

    def __init__(self, fetcher: HttpFetcher, max_pages: int = 2) -> None:
        self.fetcher = fetcher
        self.max_pages = max_pages

    def fetch_offers(self) -> list[Offer]:
        offers: list[Offer] = []
        raw_cards_total = 0

        for page in range(1, self.max_pages + 1):
            params = {
                "query": "alternance",
                "aroundQuery": "Paris",
                "page": str(page),
            }
            response = self.fetcher.get(self.BASE_URL, params=params)
            page_offers, raw_cards = self.parse_html(response.text)
            raw_cards_total += raw_cards
            offers.extend(page_offers)

        deduped = _dedupe_by_url(offers)
        LOGGER.info(
            "source_fetch_completed",
            extra={"source": self.name, "raw_cards": raw_cards_total, "extracted": len(deduped)},
        )
        return deduped

    def parse_html(self, html_text: str) -> tuple[list[Offer], int]:
        """Parse WTTJ HTML with priority to structured embedded JSON."""

        structured = _extract_next_data_jobs(html_text)
        if structured:
            return structured, len(structured)

        cards = re.findall(r"(<article\b.*?</article>)", html_text, flags=re.IGNORECASE | re.DOTALL)
        offers: list[Offer] = []

        for card in cards:
            href = _extract_text(card, [r"<a[^>]*href=['\"]([^'\"]*/jobs/[^'\"]*)['\"]"])
            title = _extract_text(card, [r"<h4[^>]*>(.*?)</h4>", r"<h3[^>]*>(.*?)</h3>"])
            company = _extract_text(card, [r"data-testid=['\"]company-name['\"][^>]*>(.*?)</", r"<h5[^>]*>(.*?)</h5>"])
            location = _extract_text(card, [r"data-testid=['\"]job-location['\"][^>]*>(.*?)</", r"<span[^>]*class=['\"][^'\"]*location[^'\"]*['\"][^>]*>(.*?)</span>"])
            contract = _extract_text(card, [r"data-testid=['\"]job-contract['\"][^>]*>(.*?)</"])
            description = _extract_text(card, [r"<p[^>]*>(.*?)</p>"])
            date_text = _extract_text(card, [r"<time[^>]*>(.*?)</time>"])

            if not title or not href:
                continue
            offers.append(
                Offer(
                    source=self.name,
                    title=title,
                    company=company,
                    location=location,
                    contract_type=contract,
                    url=urljoin("https://www.welcometothejungle.com", href),
                    description=description,
                    published_at=_parse_iso_or_none(date_text),
                )
            )

        return _dedupe_by_url(offers), len(cards)


def _extract_next_data_jobs(html_text: str) -> list[Offer]:
    match = re.search(
        r"<script[^>]*id=['\"]__NEXT_DATA__['\"][^>]*>(.*?)</script>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    payload_raw = html.unescape(match.group(1)).strip()
    if not payload_raw:
        return []

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        return []

    offers: list[Offer] = []
    for item in _walk(payload):
        if not isinstance(item, dict):
            continue

        url = _pick(item, ["url", "absolute_url", "job_url", "href"]) or ""
        title = _pick(item, ["title", "name", "jobTitle"]) or ""
        company = _pick(item, ["company", "organization", "company_name", "companyName"]) or ""
        location = _pick(item, ["location", "office", "city", "addressLocality"]) or ""
        contract = _pick(item, ["contract_type", "contractType", "employmentType", "type"]) or ""
        description = _pick(item, ["description", "pitch", "summary"]) or ""
        date_raw = _pick(item, ["published_at", "publication_date", "datePosted", "publishedAt"]) or ""

        if not title or not url or "/jobs/" not in str(url):
            continue

        offers.append(
            Offer(
                source="welcome_to_the_jungle",
                title=_clean_text(title),
                company=_clean_text(company),
                location=_clean_text(location),
                contract_type=_clean_text(contract),
                url=urljoin("https://www.welcometothejungle.com", str(url)),
                description=_clean_text(description),
                published_at=_parse_iso_or_none(str(date_raw)),
            )
        )

    return _dedupe_by_url(offers)


def _pick(data: dict, keys: list[str]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            nested = value.get("name")
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _walk(obj: object):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _parse_iso_or_none(text: str) -> datetime | None:
    if not text:
        return None
    candidate = text.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", candidate)
        if match:
            return datetime.fromisoformat(match.group(1))
        return None


def _extract_text(block: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, block, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _clean_text(match.group(1))
    return ""


def _clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _dedupe_by_url(offers: list[Offer]) -> list[Offer]:
    seen: set[str] = set()
    result: list[Offer] = []
    for offer in offers:
        if offer.url in seen:
            continue
        seen.add(offer.url)
        result.append(offer)
    return result
