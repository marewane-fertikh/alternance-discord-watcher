from watcher.domain.models import Offer
from watcher.filters.contract import is_contract_accepted
from watcher.filters.location import is_location_accepted
from watcher.filters.relevance import score_offer


def test_contract_filter_accepts_alternance() -> None:
    assert is_contract_accepted("Contrat d'apprentissage")


def test_contract_filter_rejects_cdi() -> None:
    assert not is_contract_accepted("CDI")


def test_location_filter_accepts_paris() -> None:
    assert is_location_accepted("Paris")


def test_location_filter_rejects_remote_without_anchor() -> None:
    assert not is_location_accepted("Full remote", "Remote only")


def test_relevance_scoring_high_for_backend_python() -> None:
    offer = Offer(
        source="x",
        title="Alternance Backend Developer Python",
        company="Acme",
        location="Paris",
        contract_type="Alternance",
        url="https://example.com/a",
        description="API Docker Kubernetes",
    )
    result = score_offer(offer)
    assert result.score >= 60
    assert result.accepted
