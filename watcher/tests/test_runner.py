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


def _offer(
    url: str,
    *,
    published_at: datetime | None = None,
    contract: str = "Alternance",
    location: str = "Paris",
    title: str = "Alternance Backend Developer Python",
    description: str = "API Docker",
) -> Offer:
    return Offer(
        source="dummy",
        title=title,
        company="Acme",
        location=location,
        contract_type=contract,
        url=url,
        description=description,
        published_at=published_at,
    )


def test_bootstrap_stores_without_publish(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "offers.db")
    notifier = DummyNotifier()
    offer = _offer("https://example.com/1", published_at=datetime.utcnow() - timedelta(days=2))
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


def test_rejection_counters_with_source_breakdown(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "offers.db")
    notifier = DummyNotifier()
    offers = [
        _offer("https://example.com/contract", contract="CDI", title="Ingénieur logiciel"),
        _offer("https://example.com/location", location="Lyon"),
        _offer("https://example.com/score", title="Alternance SEO marketing", description="support helpdesk"),
        _offer("https://example.com/ok"),
    ]
    runner = Runner([DummyAdapter(offers)], store, notifier)

    result = runner.run(RunOptions(min_score=60))

    assert result["rejected_contract"] == 1
    assert result["rejected_location"] == 1
    assert result["rejected_score"] == 1
    assert result["accepted"] == 1
    assert result["source_dummy_rejected_contract"] == 1
    assert result["source_dummy_rejected_location"] == 1
    assert result["source_dummy_rejected_score"] == 1
    assert result["source_dummy_accepted"] == 1
