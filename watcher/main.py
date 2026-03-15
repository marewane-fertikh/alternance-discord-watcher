"""CLI entrypoint for alternance watcher."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from watcher.adapters.base import HttpFetcher
from watcher.adapters.hellowork import HelloworkAdapter
from watcher.adapters.welcome_to_the_jungle import WelcomeToTheJungleAdapter
from watcher.app.runner import RunOptions, Runner
from watcher.config.settings import load_settings
from watcher.notifier.discord_webhook import DiscordWebhookNotifier
from watcher.storage.sqlite_store import SQLiteStore


def configure_logging(level: str) -> None:
    """Configure JSON-ish log output for journalctl parsing."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Alternance Discord watcher")
    parser.add_argument("--once", action="store_true", help="Run once (default behavior).")
    parser.add_argument("--dry-run", action="store_true", help="Do not post to Discord.")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap mode with lookback.")
    parser.add_argument("--publish-backfill", action="store_true", help="Publish bootstrap matches to Discord.")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging.")
    return parser.parse_args()


def main() -> int:
    """Program entrypoint."""

    args = parse_args()
    settings = load_settings()
    configure_logging("DEBUG" if args.verbose else settings.log_level)

    fetcher = HttpFetcher(
        timeout=settings.request_timeout_seconds,
        delay_seconds=settings.request_delay_seconds,
        user_agent=settings.user_agent,
    )
    adapters = [
        HelloworkAdapter(fetcher, max_pages=settings.hellowork_max_pages),
        WelcomeToTheJungleAdapter(fetcher, max_pages=settings.wttj_max_pages),
    ]
    store = SQLiteStore(settings.sqlite_db_path)
    notifier = DiscordWebhookNotifier(settings.discord_webhook_url, timeout=settings.request_timeout_seconds)
    runner = Runner(adapters=adapters, store=store, notifier=notifier)

    options = RunOptions(
        dry_run=args.dry_run,
        bootstrap=args.bootstrap,
        publish_backfill=args.publish_backfill,
        min_score=settings.min_score,
        max_posts=settings.max_posts_per_run,
        lookback_days=settings.bootstrap_lookback_days,
    )

    counters = runner.run(options)
    print(json.dumps(counters))
    return 0


if __name__ == "__main__":
    sys.exit(main())
