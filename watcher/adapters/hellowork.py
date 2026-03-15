"""Hellowork adapter implementation."""

from __future__ import annotations

from datetime import datetime
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from watcher.adapters.base import HttpFetcher, SourceAdapter, parse_text, safe_iter
from watcher.domain.models import Offer


LOGGER = logging.getLogger(__name__)


class HelloworkAdapter(SourceAdapter):
    """Fetch apprenticeship offers from Hellowork search page."""

    name = "hellowork"
    BASE_URL = "https://www.hellowork.com/fr-fr/emploi/recherche.html"

    def __init__(self, fetcher: HttpFetcher) -> None:
        self.fetcher = fetcher

    def fetch_offers(self) -> list[Offer]:
        params = {
            "k": "alternance developpeur",
            "l": "Ile-de-France",
        }
        response = self.fetcher.get(self.BASE_URL, params=params)
        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("article")
        offers: list[Offer] = []

        for card in safe_iter(cards):
            title_node = card.select_one("a[data-cy='offerTitle']") or card.select_one("h2 a")
            url = ""
            if title_node and title_node.has_attr("href"):
                url = urljoin("https://www.hellowork.com", str(title_node["href"]))
            title = parse_text(title_node)
            company = parse_text(card.select_one("[data-cy='companyName']") or card.select_one(".tw-text-s") or card.select_one("p"))
            location = parse_text(card.select_one("[data-cy='location']") or card.select_one(".tw-text-neutral"))
            contract = parse_text(card.select_one("[data-cy='contractType']"))
            date_text = parse_text(card.select_one("time"))
            published_at = _parse_date(date_text)

            if not url or not title:
                continue

            offers.append(
                Offer(
                    source=self.name,
                    title=title,
                    company=company,
                    location=location,
                    contract_type=contract,
                    url=url,
                    description="",
                    published_at=published_at,
                )
            )

        LOGGER.info("source_fetch_completed", extra={"source": self.name, "count": len(offers)})
        return offers


def _parse_date(raw: str) -> datetime | None:
    """Parse common FR date from text."""

    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None
