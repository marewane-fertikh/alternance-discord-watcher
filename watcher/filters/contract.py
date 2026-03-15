"""Contract filtering rules."""

from __future__ import annotations


ACCEPT_KEYWORDS = [
    "alternance",
    "apprentissage",
    "contrat d'apprentissage",
    "work-study",
    "work study",
]

REJECT_KEYWORDS = [
    "cdi",
    "cdd",
    "stage",
    "internship",
    "freelance",
]


def is_contract_accepted(contract_text: str, title: str = "", description: str = "") -> bool:
    """Return whether the offer contract is apprenticeship-compatible."""

    text = f"{contract_text} {title} {description}".lower()
    if any(word in text for word in REJECT_KEYWORDS):
        return False
    return any(word in text for word in ACCEPT_KEYWORDS)
