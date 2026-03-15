"""Application runner orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from watcher.adapters.base import SourceAdapter
from watcher.domain.models import Offer, ScoreResult
from watcher.filters.contract import is_contract_accepted
from watcher.filters.location import is_location_accepted
from watcher.filters.relevance import score_offer
from watcher.notifier.discord_webhook import DiscordWebhookNotifier
from watcher.storage.sqlite_store import SQLiteStore


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunOptions:
    dry_run: bool = False
    bootstrap: bool = False
    publish_backfill: bool = False
    min_score: int = 60
    max_posts: int = 20
    lookback_days: int = 30


class Runner:
    """Coordinates source fetch, filtering, dedupe, storage and notifications."""

    def __init__(self, adapters: list[SourceAdapter], store: SQLiteStore, notifier: DiscordWebhookNotifier) -> None:
        self.adapters = adapters
        self.store = store
        self.notifier = notifier

    def run(self, options: RunOptions) -> dict[str, int]:
        """Execute one run and return counters."""

        counters: dict[str, int] = {
            "fetched": 0,
            "accepted": 0,
            "posted": 0,
            "rejected_contract": 0,
            "rejected_location": 0,
            "rejected_score": 0,
            "skipped_existing": 0,
        }
        candidates: list[tuple[Offer, ScoreResult]] = []

        for adapter in self.adapters:
            source = adapter.name
            self._init_source_counters(counters, source)
            try:
                offers = adapter.fetch_offers()
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("source_failed", extra={"source": source, "error": str(exc)})
                continue

            _inc(counters, "fetched", len(offers))
            _inc(counters, f"source_{source}_fetched", len(offers))

            for offer in offers:
                if options.bootstrap and not _within_lookback(offer, options.lookback_days):
                    _inc(counters, f"source_{source}_rejected_lookback")
                    continue

                if not is_contract_accepted(offer.contract_type, offer.title, offer.description):
                    _inc(counters, "rejected_contract")
                    _inc(counters, f"source_{source}_rejected_contract")
                    LOGGER.debug("offer_rejected_contract", extra={"source": source, "url": offer.url, "contract": offer.contract_type})
                    continue

                if not is_location_accepted(offer.location, offer.description):
                    _inc(counters, "rejected_location")
                    _inc(counters, f"source_{source}_rejected_location")
                    LOGGER.debug("offer_rejected_location", extra={"source": source, "url": offer.url, "location": offer.location})
                    continue

                result = score_offer(offer)
                if result.score < options.min_score:
                    _inc(counters, "rejected_score")
                    _inc(counters, f"source_{source}_rejected_score")
                    LOGGER.debug("offer_rejected_score", extra={"source": source, "url": offer.url, "score": result.score})
                    continue

                if self.store.exists(offer):
                    _inc(counters, "skipped_existing")
                    _inc(counters, f"source_{source}_skipped_existing")
                    LOGGER.debug("offer_skipped_existing", extra={"source": source, "url": offer.url})
                    continue

                _inc(counters, "accepted")
                _inc(counters, f"source_{source}_accepted")
                candidates.append((offer, result))

        candidates.sort(key=lambda item: (item[1].score, item[0].published_at or datetime.min), reverse=True)
        to_process = candidates[: options.max_posts]

        for offer, result in to_process:
            source = offer.source
            should_publish = (not options.bootstrap) or options.publish_backfill
            sent = False

            if should_publish and not options.dry_run:
                sent = self.notifier.send_offer(offer, result)
                if sent:
                    _inc(counters, "posted")
                    _inc(counters, f"source_{source}_posted")

            self.store.save_offer(offer, result.score, result.confidence, result.explanation, sent=sent)

        LOGGER.info("run_completed", extra=counters)
        return counters

    def _init_source_counters(self, counters: dict[str, int], source: str) -> None:
        for key in [
            "fetched",
            "accepted",
            "posted",
            "rejected_contract",
            "rejected_location",
            "rejected_score",
            "rejected_lookback",
            "skipped_existing",
        ]:
            counters.setdefault(f"source_{source}_{key}", 0)


def _inc(counters: dict[str, int], key: str, value: int = 1) -> None:
    counters[key] = counters.get(key, 0) + value


def _within_lookback(offer: Offer, lookback_days: int) -> bool:
    if offer.published_at is None:
        return True
    return offer.published_at >= (datetime.utcnow() - timedelta(days=lookback_days))
