"""Relevance scoring and explanation."""

from __future__ import annotations

from dataclasses import dataclass

from watcher.domain.models import Offer, ScoreResult


@dataclass(frozen=True)
class ScoreWeights:
    title_match: int = 45
    description_domain_match: int = 20
    stack_match: int = 20
    negative_penalty: int = 45
    senior_penalty: int = 10
    software_context_bonus: int = 10


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
    "devops",
    "cloud",
]
DOMAIN_KEYWORDS = ["devops", "cloud", "api", "architecture logicielle", "microservices", "kubernetes", "docker", "platform"]
STACK_KEYWORDS = ["python", "java", "typescript", "node", "go", "spring", "django", "fastapi"]
SOFTWARE_CONTEXT = ["logiciel", "software", "engineering", "developpement", "développement", "backend"]

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
    title_text = offer.title.lower()
    desc_text = offer.description.lower()
    merged_text = f"{title_text} {desc_text}"

    positive: list[str] = []
    negative: list[str] = []
    score = 0

    title_hits = [keyword for keyword in TITLE_KEYWORDS if keyword in title_text]
    if title_hits:
        score += min(w.title_match, 20 + 10 * len(title_hits))
        positive.extend([f"title:{value}" for value in title_hits[:2]])

    domain_hits = [keyword for keyword in DOMAIN_KEYWORDS if keyword in merged_text]
    if domain_hits:
        score += min(w.description_domain_match, 8 + 4 * len(domain_hits))
        positive.extend([f"domain:{value}" for value in domain_hits[:2]])

    stack_hits = [keyword for keyword in STACK_KEYWORDS if keyword in merged_text]
    if stack_hits:
        score += min(w.stack_match, 5 + 5 * len(stack_hits))
        positive.extend([f"stack:{value}" for value in stack_hits[:2]])

    if any(keyword in merged_text for keyword in SOFTWARE_CONTEXT):
        score += w.software_context_bonus
        positive.append("context:software")

    neg_hits = [keyword for keyword in NEGATIVE_KEYWORDS if keyword in merged_text]
    if neg_hits:
        score -= min(w.negative_penalty, 15 * len(neg_hits))
        negative.extend([f"negative:{value}" for value in neg_hits[:2]])

    if any(keyword in merged_text for keyword in SENIOR_HINTS):
        score -= w.senior_penalty
        negative.append("seniority:high")

    score = max(0, min(100, score))
    accepted = score >= 60
    confidence = "high confidence" if score >= 75 else "medium confidence"

    explanation_parts = ["contract ok", "location ok"] + positive + negative
    return ScoreResult(
        accepted=accepted,
        score=score,
        confidence=confidence,
        explanation=", ".join(explanation_parts[:7]),
        positive_signals=positive,
        negative_signals=negative,
    )
