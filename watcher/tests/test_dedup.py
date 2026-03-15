from watcher.filters.dedup import canonicalize_url, fallback_dedupe_key


def test_canonicalize_url_removes_tracking() -> None:
    url = "HTTPS://Example.com/jobs/123/?utm_source=x&gclid=1&a=2#frag"
    assert canonicalize_url(url) == "https://example.com/jobs/123?a=2"


def test_fallback_key_is_stable() -> None:
    key1 = fallback_dedupe_key("SRC", "Acme", "Dev", "Paris")
    key2 = fallback_dedupe_key("src", "acme", "dev", "paris")
    assert key1 == key2
