"""Relevance scoring and explanation."""

from __future__ import annotations

from dataclasses import dataclass

from watcher.domain.models import Offer, ScoreResult


@dataclass(frozen=True)
class ScoreWeights:
    title_match: int = 40
    domain_match: int = 25
    stack_match: int = 20
    negative_penalty: int = 40
    senior_penalty: int = 10


TITLE_KEYWORDS = [
    "backend",
    "back-end",
    "software engineer",
    "software developer",
    "developer",
    "développeur",
    "développeuse",
    "ingénieur logiciel",
    "ingénieur développement",
    "platform engineer",
    "sre",
    "architecte logiciel",
]

DOMAIN_KEYWORDS = ["devops", "cloud", "api", "architecture logicielle", "microservices", "kubernetes", "docker"]
STACK_KEYWORDS = ["python", "java", "typescript", "node", "go", "spring", "django", "fastapi"]
NEGATIVE_KEYWORDS = [
    "commercial",
    "business developer",
    "marketing",
    "seo",
    "support",
    "helpdesk",
    "technicien support",
    "no-code",
    "data analyst",
    "manual qa",
    "administratif",
    "assistant commercial",
]


SENIOR_HINTS = ["senior", "lead", "10+ ans", "7+ ans"]


def score_offer(offer: Offer, weights: ScoreWeights | None = None) -> ScoreResult:
    """Compute deterministic score [0..100] with textual explanation."""

    w = weights or ScoreWeights()
    text = f"{offer.title} {offer.description}".lower()

    positive: list[str] = []
    negative: list[str] = []
    score = 0

    title_hits = [k for k in TITLE_KEYWORDS if k in text]
    if title_hits:
        score += w.title_match
        positive.append(f"title:{title_hits[0]}")

    domain_hits = [k for k in DOMAIN_KEYWORDS if k in text]
    if domain_hits:
        score += min(w.domain_match, 10 + 5 * len(domain_hits))
        positive.extend([f"domain:{k}" for k in domain_hits[:2]])

    stack_hits = [k for k in STACK_KEYWORDS if k in text]
    if stack_hits:
        score += min(w.stack_match, 5 + 5 * len(stack_hits))
        positive.extend([f"stack:{k}" for k in stack_hits[:2]])

    neg_hits = [k for k in NEGATIVE_KEYWORDS if k in text]
    if neg_hits:
        score -= min(w.negative_penalty, 15 * len(neg_hits))
        negative.extend([f"negative:{k}" for k in neg_hits[:2]])

    if any(k in text for k in SENIOR_HINTS):
        score -= w.senior_penalty
        negative.append("seniority:high")

    score = max(0, min(100, score))
    accepted = score >= 60
    confidence = "high confidence" if score >= 75 else "medium confidence"

    explanation_parts = ["contract ok", "location ok"] + positive
    if negative:
        explanation_parts += negative

    return ScoreResult(
        accepted=accepted,
        score=score,
        confidence=confidence,
        explanation=", ".join(explanation_parts[:6]),
        positive_signals=positive,
        negative_signals=negative,
    )
