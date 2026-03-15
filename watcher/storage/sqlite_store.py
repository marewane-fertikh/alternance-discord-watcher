"""SQLite persistence layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

from watcher.domain.models import Offer
from watcher.filters.dedup import canonicalize_url, fallback_dedupe_key


class SQLiteStore:
    """Store seen and sent offers in SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    contract_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    score INTEGER,
                    confidence TEXT,
                    explanation TEXT,
                    published_at TEXT,
                    first_seen_at TEXT NOT NULL,
                    sent_at TEXT
                )
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_offers_canonical_url ON offers(canonical_url)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_offers_dedupe_key ON offers(dedupe_key)")

    def exists(self, offer: Offer) -> bool:
        canonical_url = canonicalize_url(offer.url)
        dedupe_key = fallback_dedupe_key(offer.source, offer.company, offer.title, offer.location)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM offers WHERE canonical_url = ? OR dedupe_key = ? LIMIT 1",
                (canonical_url, dedupe_key),
            ).fetchone()
        return row is not None

    def save_offer(self, offer: Offer, score: int, confidence: str, explanation: str, sent: bool) -> None:
        now = datetime.utcnow().isoformat()
        published_at = offer.published_at.isoformat() if offer.published_at else None
        canonical_url = canonicalize_url(offer.url)
        dedupe_key = fallback_dedupe_key(offer.source, offer.company, offer.title, offer.location)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO offers (
                    source, title, company, location, contract_type, url,
                    canonical_url, dedupe_key, score, confidence, explanation,
                    published_at, first_seen_at, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    offer.source,
                    offer.title,
                    offer.company,
                    offer.location,
                    offer.contract_type,
                    offer.url,
                    canonical_url,
                    dedupe_key,
                    score,
                    confidence,
                    explanation,
                    published_at,
                    now,
                    now if sent else None,
                ),
            )

    def mark_sent(self, offer: Offer) -> None:
        now = datetime.utcnow().isoformat()
        canonical_url = canonicalize_url(offer.url)
        with self._connect() as conn:
            conn.execute("UPDATE offers SET sent_at = ? WHERE canonical_url = ?", (now, canonical_url))

    def already_sent(self, offer: Offer) -> bool:
        canonical_url = canonicalize_url(offer.url)
        with self._connect() as conn:
            row = conn.execute("SELECT sent_at FROM offers WHERE canonical_url = ?", (canonical_url,)).fetchone()
        return row is not None and row[0] is not None
