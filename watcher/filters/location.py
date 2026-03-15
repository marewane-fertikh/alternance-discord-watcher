"""Île-de-France location filtering rules."""

from __future__ import annotations

import re
import unicodedata


IDF_KEYWORDS = [
    "ile-de-france",
    "paris",
    "seine-et-marne",
    "yvelines",
    "essonne",
    "hauts-de-seine",
    "seine-saint-denis",
    "val-de-marne",
    "val-d'oise",
    "la defense",
    "courbevoie",
    "levallois",
    "issy-les-moulineaux",
    "saint-denis",
    "montreuil",
    "boulogne-billancourt",
    "nanterre",
    "cergy",
    "creteil",
    "versailles",
    "asnieres",
    "argenteuil",
    "puteaux",
    "rueil-malmaison",
    "vincennes",
]

REMOTE_ONLY_KEYWORDS = ["full remote", "fully remote", "remote only", "100% remote", "teletravail complet"]
DEPARTMENT_CODES = ["75", "77", "78", "91", "92", "93", "94", "95"]


def normalize_text(value: str) -> str:
    """Normalize text for robust accent-insensitive matching."""

    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.lower()


def is_location_accepted(location: str, description: str = "") -> bool:
    """Accept if clearly tied to Île-de-France and not remote-only unanchored."""

    text = normalize_text(f"{location} {description}")
    has_idf_keyword = any(keyword in text for keyword in IDF_KEYWORDS)
    has_department_ref = _has_department_reference(text)
    has_postcode = bool(re.search(r"\b(?:75|77|78|91|92|93|94|95)\d{3}\b", text))
    has_idf = has_idf_keyword or has_department_ref or has_postcode

    remote_only = any(word in text for word in REMOTE_ONLY_KEYWORDS)
    if remote_only and not has_idf:
        return False
    return has_idf


def _has_department_reference(text: str) -> bool:
    for dept in DEPARTMENT_CODES:
        if re.search(rf"\b{dept}\b", text):
            return True
    return False
