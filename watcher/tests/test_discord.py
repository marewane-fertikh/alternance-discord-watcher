from watcher.domain.models import Offer, ScoreResult
from watcher.notifier.discord_webhook import format_discord_payload


def test_discord_payload_format() -> None:
    offer = Offer(
        source="hellowork",
        title="Alternance DevOps",
        company="Acme",
        location="Paris",
        contract_type="Alternance",
        url="https://example.com/job",
        description="",
    )
    result = ScoreResult(True, 77, "high confidence", "contract ok, location ok")
    payload = format_discord_payload(offer, result)
    embed = payload["embeds"][0]
    assert embed["title"] == offer.title
    assert embed["url"] == offer.url
    assert any(f["name"] == "Score" for f in embed["fields"])
