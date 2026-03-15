"""Contract filtering rules."""

from __future__ import annotations

import re


ACCEPT_PATTERNS = [
    r"\balternance\b",
    r"\bapprentissage\b",
    r"contrat d[’']apprentissage",
    r"contrat apprentissage",
    r"\bwork[ -]?study\b",
    r"alternance\s*/\s*apprentissage",
    r"\b\d+\s*mois\s+en\s+alternance\b",
    r"rythme\s+alternance",
]

REJECT_PATTERNS = [
    r"\bcdi\b",
    r"\bcdd\b",
    r"\bfreelance\b",
    r"\bstage\b",
    r"\binternship\b",
]


def is_contract_accepted(contract_text: str, title: str = "", description: str = "") -> bool:
    """Return whether the offer contract is apprenticeship-compatible."""

    text = _normalize_contract_text(f"{contract_text} {title} {description}")

    has_accept = any(re.search(pattern, text) for pattern in ACCEPT_PATTERNS)
    has_reject = any(re.search(pattern, text) for pattern in REJECT_PATTERNS)

    if has_reject and not has_accept:
        return False
    if re.search(r"\bstage\b", text) and not has_accept:
        return False
    return has_accept


def _normalize_contract_text(text: str) -> str:
    return text.lower().replace("’", "'")
