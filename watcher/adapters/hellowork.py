"""Hellowork adapter implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
import html
import logging
import re
from urllib.parse import urljoin

from watcher.adapters.base import HttpFetcher, SourceAdapter
from watcher.domain.models import Offer


LOGGER = logging.getLogger(__name__)


class HelloworkAdapter(SourceAdapter):
    """Fetch apprenticeship offers from Hellowork search pages."""

    name = "hellowork"
    BASE_URL = "https://www.hellowork.com/fr-fr/emploi/recherche.html"
    SEARCH_QUERIES = [
        "alternance backend",
        "alternance développeur backend",
        "alternance devops",
        "alternance cloud",
        "alternance software engineer",
        "alternance ingénieur logiciel",
    ]

    def __init__(self, fetcher: HttpFetcher, max_pages: int = 2) -> None:
        self.fetcher = fetcher
        self.max_pages = max_pages

    def fetch_offers(self) -> list[Offer]:
        offers: list[Offer] = []
        raw_cards_total = 0

        for query in self.SEARCH_QUERIES:
            for page in range(1, self.max_pages + 1):
                params = {"k": query, "l": "Ile-de-France", "p": str(page)}
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
        """Parse Hellowork listing HTML."""

        cards = re.findall(r"(<article\b.*?</article>)", html_text, flags=re.IGNORECASE | re.DOTALL)
        offers: list[Offer] = []

        for card in cards:
            href = _extract_attr(card, [r"data-cy=['\"]offerTitle['\"][^>]*href=['\"]([^'\"]+)['\"]", r"<h2[^>]*>\s*<a[^>]*href=['\"]([^'\"]+)['\"]", r"<a[^>]*href=['\"]([^'\"]+)['\"]"])
            title = _extract_text(card, [r"data-cy=['\"]offerTitle['\"][^>]*>(.*?)</a>", r"<h2[^>]*>\s*<a[^>]*>(.*?)</a>"])
            company = _extract_text(card, [r"data-cy=['\"]companyName['\"][^>]*>(.*?)</", r"data-testid=['\"]company-name['\"][^>]*>(.*?)</"])
            location = _extract_text(card, [r"data-cy=['\"]location['\"][^>]*>(.*?)</", r"data-testid=['\"]location['\"][^>]*>(.*?)</"])
            contract = _extract_text(card, [r"data-cy=['\"]contractType['\"][^>]*>(.*?)</", r"data-testid=['\"]contract-type['\"][^>]*>(.*?)</"])
            description = _extract_text(card, [r"data-cy=['\"]jobDescription['\"][^>]*>(.*?)</", r"<p[^>]*>(.*?)</p>"])
            date_text = _extract_text(card, [r"<time[^>]*>(.*?)</time>", r"data-cy=['\"]publicationDate['\"][^>]*>(.*?)</"])

            if not title or not href:
                continue

            offers.append(
                Offer(
                    source=self.name,
                    title=title,
                    company=company,
                    location=location,
                    contract_type=contract,
                    url=urljoin("https://www.hellowork.com", href),
                    description=description,
                    published_at=_parse_date(date_text),
                )
            )

        return offers, len(cards)


def _extract_text(block: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, block, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _clean_text(match.group(1))
    return ""


def _extract_attr(block: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, block, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _clean_text(match.group(1))
    return ""


def _clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _parse_date(raw: str) -> datetime | None:
    """Parse common FR absolute and relative date formats."""

    text = raw.strip().lower()
    if not text:
        return None

    now = datetime.utcnow()
    if "aujourd" in text:
        return now
    if "hier" in text:
        return now - timedelta(days=1)

    days_match = re.search(r"il y a\s*(\d+)\s*jour", text)
    if days_match:
        return now - timedelta(days=int(days_match.group(1)))

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    month_map = {
        "janvier": "01",
        "février": "02",
        "fevrier": "02",
        "mars": "03",
        "avril": "04",
        "mai": "05",
        "juin": "06",
        "juillet": "07",
        "août": "08",
        "aout": "08",
        "septembre": "09",
        "octobre": "10",
        "novembre": "11",
        "décembre": "12",
        "decembre": "12",
    }
    month_match = re.search(r"(\d{1,2})\s+([a-zéûôî]+)\s+(\d{4})", text)
    if month_match:
        day, month_raw, year = month_match.groups()
        month = month_map.get(month_raw)
        if month:
            return datetime.strptime(f"{day.zfill(2)}/{month}/{year}", "%d/%m/%Y")
    return None


def _dedupe_by_url(offers: list[Offer]) -> list[Offer]:
    seen: set[str] = set()
    deduped: list[Offer] = []
    for offer in offers:
        if offer.url in seen:
            continue
        seen.add(offer.url)
        deduped.append(offer)
    return deduped
