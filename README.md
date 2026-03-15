# Alternance Discord Watcher (Ubuntu-first MVP)

Monitors alternance/apprenticeship software-engineering offers from **Hellowork** and **Welcome to the Jungle**, filters/scorers/deduplicates them, stores state in SQLite, and posts only new relevant offers to Discord webhook.

## Architecture summary

- `watcher/adapters`: source adapters for Hellowork and WTTJ.
- `watcher/filters`: contract gate, location gate, relevance scoring, URL canonicalization and dedupe key.
- `watcher/storage`: SQLite persistence and dedupe checks.
- `watcher/notifier`: Discord incoming webhook embed formatter + sender.
- `watcher/app`: orchestration runner with bootstrap and incremental modes.
- `watcher/main.py`: CLI entrypoint.

## File tree

```text
.
├── .env.example
├── README.md
├── requirements.txt
└── watcher
    ├── __init__.py
    ├── adapters
    │   ├── __init__.py
    │   ├── base.py
    │   ├── hellowork.py
    │   └── welcome_to_the_jungle.py
    ├── app
    │   ├── __init__.py
    │   └── runner.py
    ├── config
    │   ├── __init__.py
    │   └── settings.py
    ├── data
    ├── domain
    │   ├── __init__.py
    │   └── models.py
    ├── filters
    │   ├── __init__.py
    │   ├── contract.py
    │   ├── dedup.py
    │   ├── location.py
    │   └── relevance.py
    ├── main.py
    ├── notifier
    │   ├── __init__.py
    │   └── discord_webhook.py
    ├── storage
    │   ├── __init__.py
    │   └── sqlite_store.py
    ├── systemd
    │   ├── alternance-watcher.service
    │   └── alternance-watcher.timer
    └── tests
        ├── __init__.py
        ├── test_dedup.py
        ├── test_discord.py
        ├── test_filters.py
        ├── test_runner.py
        └── test_storage.py
```

## Configuration (.env)

Copy `.env.example` to `.env` and set:

- `DISCORD_WEBHOOK_URL`
- `SQLITE_DB_PATH` (default `./data/offers.db`)
- `MIN_SCORE` (default `60`)
- `MAX_POSTS_PER_RUN` (default `20`)
- `LOG_LEVEL` (default `INFO`)
- `REQUEST_TIMEOUT_SECONDS` (default `15`)
- `REQUEST_DELAY_SECONDS` (default `1.0`)
- `USER_AGENT`
- `BOOTSTRAP_LOOKBACK_DAYS` (default `30`)
- `HELLOWORK_MAX_PAGES` (default `2`)
- `WTTJ_MAX_PAGES` (default `2`)

## Exact Ubuntu install and run commands

```bash
cd /workspace/alternance-discord-watcher
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# edit .env and set DISCORD_WEBHOOK_URL

# run tests
pytest -q

# normal incremental run
python -m watcher.main --once

# dry-run (no Discord post)
python -m watcher.main --once --dry-run

# bootstrap last 30 days into SQLite WITHOUT publishing historical offers
python -m watcher.main --once --bootstrap

# bootstrap and explicitly publish backfill
python -m watcher.main --once --bootstrap --publish-backfill
```

## Exact systemd installation/enabling commands

```bash
cd /workspace/alternance-discord-watcher
mkdir -p ~/.config/systemd/user
cp watcher/systemd/alternance-watcher.service ~/.config/systemd/user/
cp watcher/systemd/alternance-watcher.timer ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now alternance-watcher.timer

# check timer
systemctl --user list-timers | rg alternance-watcher

# inspect logs
journalctl --user -u alternance-watcher.service -f
```

## How it works

1. Runner fetches offers from Hellowork and WTTJ independently (partial failures tolerated).
2. Hard gates apply first: contract (alternance/apprentissage/work-study only), then Île-de-France location.
3. Relevance score is computed (`0..100`) with explainable weighted signals.
4. Score threshold applies (`>= MIN_SCORE`, default `60`) and confidence label:
   - `60-74`: medium confidence
   - `75+`: high confidence
5. Dedupe uses canonical URL first, then fallback hash on source+company+title+location.
6. Bootstrap mode stores recent (lookback default 30 days) offers and avoids backfill flood unless `--publish-backfill` is set.
7. Incremental mode only posts unseen accepted offers.

## Known limitations of this V1

- Source HTML can change; selectors may need updates.
- WTTJ publication date is not always explicit on listing cards, so bootstrap includes no-date entries as best-effort fallback.
- This MVP uses static HTTP parsing; no mandatory browser automation.
- LinkedIn is intentionally excluded.
- Indeed is intentionally not required.
