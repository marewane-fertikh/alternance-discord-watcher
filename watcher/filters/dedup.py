"""Deduplication helpers."""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {"gclid", "fbclid"}


def canonicalize_url(url: str) -> str:
    """Normalize URL for stable dedupe."""

    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"

    filtered_query = []
    for key, val in parse_qsl(parts.query, keep_blank_values=True):
        lk = key.lower()
        if lk.startswith("utm_") or lk in TRACKING_PARAMS:
            continue
        filtered_query.append((key, val))
    query = urlencode(sorted(filtered_query))
    return urlunsplit((scheme, netloc, path, query, ""))


def fallback_dedupe_key(source: str, company: str, title: str, location: str) -> str:
    """Build stable fallback dedupe key."""

    base = "|".join([
        source.strip().lower(),
        company.strip().lower(),
        title.strip().lower(),
        location.strip().lower(),
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
