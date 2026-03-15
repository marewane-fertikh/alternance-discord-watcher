from pathlib import Path

from watcher.adapters.base import HttpFetcher
from watcher.adapters.hellowork import HelloworkAdapter
from watcher.adapters.welcome_to_the_jungle import WelcomeToTheJungleAdapter


def test_hellowork_parse_html_fixture() -> None:
    html = Path("watcher/tests/fixtures/hellowork_list.html").read_text(encoding="utf-8")
    adapter = HelloworkAdapter(HttpFetcher(timeout=1, delay_seconds=0, user_agent="ua"), max_pages=1)

    offers, raw_count = adapter.parse_html(html)

    assert raw_count == 2
    assert len(offers) == 2
    assert offers[0].title.startswith("Alternance Développeur Backend")
    assert offers[0].company == "Acme"
    assert offers[0].description == "API FastAPI Docker"
    assert offers[0].published_at is not None


def test_wttj_parse_html_prefers_next_data() -> None:
    html = Path("watcher/tests/fixtures/wttj_list.html").read_text(encoding="utf-8")
    adapter = WelcomeToTheJungleAdapter(HttpFetcher(timeout=1, delay_seconds=0, user_agent="ua"), max_pages=1)

    offers, raw_count = adapter.parse_html(html)

    assert raw_count == 2
    assert len(offers) == 2
    assert offers[0].source == "welcome_to_the_jungle"
    assert offers[0].url.startswith("https://www.welcometothejungle.com/")
    assert offers[1].location == "Courbevoie"
