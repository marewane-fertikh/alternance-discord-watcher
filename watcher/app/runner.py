"""Application runner orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from watcher.adapters.base import SourceAdapter
from watcher.domain.models import Offer
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

        counters = {"fetched": 0, "accepted": 0, "posted": 0, "skipped_existing": 0}
        candidates: list[tuple[Offer, int, object]] = []

        for adapter in self.adapters:
            try:
                offers = adapter.fetch_offers()
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("source_failed", extra={"source": adapter.name, "error": str(exc)})
                continue

            counters["fetched"] += len(offers)
            for offer in offers:
                if options.bootstrap and not _within_lookback(offer, options.lookback_days):
                    continue
                if not is_contract_accepted(offer.contract_type, offer.title, offer.description):
                    continue
                if not is_location_accepted(offer.location, offer.description):
                    continue
                result = score_offer(offer)
                if result.score < options.min_score:
                    continue
                if self.store.exists(offer):
                    counters["skipped_existing"] += 1
                    continue
                counters["accepted"] += 1
                candidates.append((offer, result.score, result))

        candidates.sort(key=lambda item: (item[1], item[0].published_at or datetime.min), reverse=True)
        to_process = candidates[: options.max_posts]

        for offer, _, result in to_process:
            should_publish = (not options.bootstrap) or options.publish_backfill
            sent = False
            if should_publish and not options.dry_run:
                sent = self.notifier.send_offer(offer, result)
                if sent:
                    counters["posted"] += 1
            self.store.save_offer(offer, result.score, result.confidence, result.explanation, sent=sent)

        LOGGER.info("run_completed", extra=counters)
        return counters


def _within_lookback(offer: Offer, lookback_days: int) -> bool:
    if offer.published_at is None:
        return True
    return offer.published_at >= (datetime.utcnow() - timedelta(days=lookback_days))
