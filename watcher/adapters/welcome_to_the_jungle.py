"""Welcome to the Jungle adapter implementation."""

from __future__ import annotations

from datetime import datetime
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from watcher.adapters.base import HttpFetcher, SourceAdapter, parse_text, safe_iter
from watcher.domain.models import Offer


LOGGER = logging.getLogger(__name__)


class WelcomeToTheJungleAdapter(SourceAdapter):
    """Fetch apprenticeship offers from WTTJ public search results."""

    name = "welcome_to_the_jungle"
    BASE_URL = "https://www.welcometothejungle.com/fr/jobs"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    def fetch_offers(self) -> list[Offer]:
        params = {
            "query": "alternance developpeur",
            "aroundQuery": "Paris",
            "refinementList[contract_type_names.fr][0]": "Apprentissage",
        }
        response = self.fetcher.get(self.BASE_URL, params=params)
        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("a[href*='/fr/companies/']")
        offers: list[Offer] = []

        for link in safe_iter(cards):
            href = str(link.get("href", ""))
            title = parse_text(link.select_one("h4") or link)
            company = parse_text(link.select_one("span") or link.select_one("h3"))
            meta_text = parse_text(link)
            location = _extract_location(meta_text)
            contract = _extract_contract(meta_text)
            published_at = None

            if not href or not title:
                continue

            offers.append(
                Offer(
                    source=self.name,
                    title=title,
                    company=company,
                    location=location,
                    contract_type=contract,
                    url=urljoin("https://www.welcometothejungle.com", href),
                    description=meta_text,
                    published_at=published_at,
                )
            )

        LOGGER.info("source_fetch_completed", extra={"source": self.name, "count": len(offers)})
        return _dedupe_by_url(offers)


def _extract_location(text: str) -> str:
    for marker in ["Paris", "Île-de-France", "Ile-de-France", "Boulogne", "Nanterre"]:
        if marker.lower() in text.lower():
            return marker
    return ""


def _extract_contract(text: str) -> str:
    for marker in ["Alternance", "Apprentissage", "Work-study"]:
        if marker.lower() in text.lower():
            return marker
    return ""


def _dedupe_by_url(offers: list[Offer]) -> list[Offer]:
    seen: set[str] = set()
    result: list[Offer] = []
    for offer in offers:
        if offer.url in seen:
            continue
        seen.add(offer.url)
        result.append(offer)
    return result
