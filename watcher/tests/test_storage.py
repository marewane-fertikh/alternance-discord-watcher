from pathlib import Path

from watcher.domain.models import Offer
from watcher.storage.sqlite_store import SQLiteStore


def _offer(url: str = "https://example.com/jobs/1") -> Offer:
    return Offer(
        source="hellowork",
        title="Alternance Backend Developer",
        company="Acme",
        location="Paris",
        contract_type="Alternance",
        url=url,
        description="python",
    )


def test_sqlite_persistence_and_sent_flag(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "offers.db")
    offer = _offer()
    assert not store.exists(offer)
    store.save_offer(offer, score=80, confidence="high confidence", explanation="ok", sent=False)
    assert store.exists(offer)
    assert not store.already_sent(offer)
    store.mark_sent(offer)
    assert store.already_sent(offer)
