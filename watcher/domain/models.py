"""Domain models for offers and scoring results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Offer:
    """Represents a parsed job offer from a source."""

    source: str
    title: str
    company: str
    location: str
    contract_type: str
    url: str
    description: str = ""
    published_at: Optional[datetime] = None


@dataclass(slots=True)
class ScoreResult:
    """Represents scoring outcome for an offer."""

    accepted: bool
    score: int
    confidence: str
    explanation: str
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
