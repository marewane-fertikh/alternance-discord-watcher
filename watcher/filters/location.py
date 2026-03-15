"""Île-de-France location filtering rules."""

from __future__ import annotations


IDF_KEYWORDS = [
    "île-de-france",
    "ile-de-france",
    "paris",
    "seine-et-marne",
    "yvelines",
    "essonne",
    "hauts-de-seine",
    "seine-saint-denis",
    "val-de-marne",
    "val-d'oise",
    "75",
    "77",
    "78",
    "91",
    "92",
    "93",
    "94",
    "95",
    "nanterre",
    "boulogne",
    "saint-denis",
    "creteil",
    "évry",
]


REMOTE_ONLY_KEYWORDS = ["full remote", "fully remote", "remote only", "100% remote"]


def is_location_accepted(location: str, description: str = "") -> bool:
    """Accept if clearly tied to Île-de-France."""

    text = f"{location} {description}".lower()
    has_idf = any(word in text for word in IDF_KEYWORDS)
    remote_only = any(word in text for word in REMOTE_ONLY_KEYWORDS)
    if remote_only and not has_idf:
        return False
    return has_idf
