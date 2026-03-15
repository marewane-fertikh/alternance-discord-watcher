"""Discord webhook notifier."""

from __future__ import annotations

import json
import logging
from urllib.request import Request, urlopen

from watcher.domain.models import Offer, ScoreResult


LOGGER = logging.getLogger(__name__)


def format_discord_payload(offer: Offer, result: ScoreResult) -> dict:
    """Build Discord webhook payload with single embed."""

    color = 0xF1C40F if result.confidence == "medium confidence" else 0x2ECC71
    return {
        "embeds": [
            {
                "title": offer.title,
                "url": offer.url,
                "color": color,
                "fields": [
                    {"name": "Company", "value": offer.company or "N/A", "inline": True},
                    {"name": "Source", "value": offer.source, "inline": True},
                    {"name": "Location", "value": offer.location or "N/A", "inline": True},
                    {"name": "Contract", "value": offer.contract_type or "N/A", "inline": True},
                    {"name": "Score", "value": str(result.score), "inline": True},
                    {"name": "Confidence", "value": result.confidence, "inline": True},
                    {"name": "Why matched", "value": result.explanation[:1000], "inline": False},
                ],
            }
        ]
    }


class DiscordWebhookNotifier:
    """Notifier that sends offers to Discord incoming webhook."""

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send_offer(self, offer: Offer, result: ScoreResult) -> bool:
        """Send an offer embed, return True on success."""

        if not self.webhook_url:
            LOGGER.warning("discord_webhook_missing")
            return False

        payload = format_discord_payload(offer, result)
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                status = getattr(response, "status", 200)
            return 200 <= status < 300
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("discord_post_failed", extra={"url": offer.url, "error": str(exc)})
            return False
