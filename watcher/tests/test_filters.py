from watcher.domain.models import Offer
from watcher.filters.contract import is_contract_accepted
from watcher.filters.location import is_location_accepted
from watcher.filters.relevance import score_offer


def test_contract_filter_accepts_variants() -> None:
    assert is_contract_accepted("Contrat d'apprentissage")
    assert is_contract_accepted("12 mois en alternance")
    assert is_contract_accepted("Rythme alternance")


def test_contract_filter_rejects_cdi() -> None:
    assert not is_contract_accepted("CDI")


def test_location_filter_accepts_idf_city_and_dept() -> None:
    assert is_location_accepted("Courbevoie")
    assert is_location_accepted("75013 Paris")
    assert is_location_accepted("Le poste est situé dans le 92", "La Défense")


def test_location_filter_rejects_remote_without_anchor() -> None:
    assert not is_location_accepted("Full remote", "Remote only")


def test_relevance_scoring_high_for_backend_python_with_description_signals() -> None:
    offer = Offer(
        source="x",
        title="Alternance Backend Developer",
        company="Acme",
        location="Paris",
        contract_type="Alternance",
        url="https://example.com/a",
        description="Python API Docker Kubernetes software engineering",
    )
    result = score_offer(offer)
    assert result.score >= 75
    assert result.accepted
