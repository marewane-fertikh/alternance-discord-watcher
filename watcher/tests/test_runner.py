from datetime import datetime, timedelta
from pathlib import Path

from watcher.adapters.base import SourceAdapter
from watcher.app.runner import RunOptions, Runner
from watcher.domain.models import Offer
from watcher.notifier.discord_webhook import DiscordWebhookNotifier
from watcher.storage.sqlite_store import SQLiteStore


class DummyAdapter(SourceAdapter):
    name = "dummy"

    def __init__(self, offers: list[Offer]) -> None:
        self._offers = offers

    def fetch_offers(self) -> list[Offer]:
        return self._offers


class DummyNotifier(DiscordWebhookNotifier):
    def __init__(self) -> None:
        super().__init__("", timeout=1)
        self.sent_urls: list[str] = []

    def send_offer(self, offer: Offer, result) -> bool:  # type: ignore[override]
        self.sent_urls.append(offer.url)
        return True


def _offer(url: str, published_at: datetime | None = None) -> Offer:
    return Offer(
        source="dummy",
        title="Alternance Backend Developer Python",
        company="Acme",
        location="Paris",
        contract_type="Alternance",
        url=url,
        description="API Docker",
        published_at=published_at,
    )


def test_bootstrap_stores_without_publish(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "offers.db")
    notifier = DummyNotifier()
    offer = _offer("https://example.com/1", datetime.utcnow() - timedelta(days=2))
    runner = Runner([DummyAdapter([offer])], store, notifier)

    result = runner.run(RunOptions(bootstrap=True, publish_backfill=False, dry_run=False))
    assert result["accepted"] == 1
    assert result["posted"] == 0
    assert store.exists(offer)


def test_prevent_reposting_already_stored_offer(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "offers.db")
    notifier = DummyNotifier()
    offer = _offer("https://example.com/1")
    store.save_offer(offer, score=80, confidence="high confidence", explanation="ok", sent=True)
    runner = Runner([DummyAdapter([offer])], store, notifier)

    result = runner.run(RunOptions())
    assert result["skipped_existing"] == 1
    assert result["posted"] == 0
