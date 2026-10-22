from types import SimpleNamespace

from app.sources import SearchProviderError, _fetch_html, _source_from_result, build_search_queries, search_web


class FakeDDGS:
    calls: list[tuple[str, dict[str, object]]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def __enter__(self) -> "FakeDDGS":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def text(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        type(self).calls.append((query, kwargs))
        return [{
            "title": "Grid energy storage",
            "href": "https://example.org/grid-storage",
            "body": "A recent report on grid storage.",
        }]


def test_search_queries_are_derived_from_domain_and_question() -> None:
    queries = build_search_queries("battery storage", "What changed in battery storage?")

    assert queries[0] == ("What changed in battery storage?", None)
    assert queries[1] == ("battery storage latest developments", "y")
    assert len(queries) == 3


def test_search_web_fans_out_and_returns_traceable_sources(monkeypatch) -> None:
    FakeDDGS.calls = []
    monkeypatch.setattr("app.sources.DDGS", FakeDDGS)
    monkeypatch.setattr("app.sources._fetch_html", lambda url: None)

    sources = search_web("battery storage", "What changed in battery storage?")

    assert len(FakeDDGS.calls) == 3
    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.org/grid-storage"
    assert sources[0]["title"] == "Grid energy storage"
    assert sources[0]["excerpt"] == "A recent report on grid storage."
    assert sources[0]["query"] == "What changed in battery storage?"
    assert sources[0]["provider"] == "ddgs"
    assert sources[0]["id"]
    assert sources[0]["retrieved_at"]


def test_search_web_deduplicates_urls_across_queries(monkeypatch) -> None:
    class DuplicateDDGS(FakeDDGS):
        def text(self, query: str, **kwargs: object) -> list[dict[str, object]]:
            type(self).calls.append((query, kwargs))
            return [
                {"title": "First result", "href": "https://example.org/story#top", "body": "First snippet"},
                {"title": "Duplicate", "href": "https://example.org/story", "body": "Duplicate snippet"},
            ]

    DuplicateDDGS.calls = []
    monkeypatch.setattr("app.sources.DDGS", DuplicateDDGS)
    monkeypatch.setattr("app.sources._fetch_html", lambda url: None)

    sources = search_web("energy storage", "What is new in energy storage?")

    assert len(DuplicateDDGS.calls) == 3
    assert len(sources) == 1
    assert sources[0]["title"] == "First result"


def test_source_uses_extracted_article_and_publication_metadata(monkeypatch) -> None:
    html = "<html><head><title>Original title</title></head><body><article>Article text</article></body></html>"
    monkeypatch.setattr("app.sources._fetch_html", lambda url: (html, url))
    monkeypatch.setattr(
        "app.sources.trafilatura.extract_metadata",
        lambda html, default_url: SimpleNamespace(title="Publisher title", sitename="Research Journal", date="2025-02-10T00:00:00Z"),
    )
    monkeypatch.setattr("app.sources.trafilatura.extract", lambda html, url, favor_precision: "A grounded article body with methods and findings.")

    source = _source_from_result(
        {"title": "Search title", "href": "https://example.org/report", "body": "Search result summary."},
        "research report query",
    )

    assert source is not None
    assert source["title"] == "Publisher title"
    assert source["publisher"] == "Research Journal"
    assert source["published_at"] == "2025-02-10"
    assert source["content"] == "A grounded article body with methods and findings."
    assert source["excerpt"] == source["content"]
    assert source["search_snippet"] == "Search result summary."


def test_browser_challenge_page_falls_back_to_search_snippet(monkeypatch) -> None:
    html = "<html><head><title>Client Challenge</title></head><body>Page could not load</body></html>"
    monkeypatch.setattr("app.sources._fetch_html", lambda url: (html, url))
    monkeypatch.setattr(
        "app.sources.trafilatura.extract_metadata",
        lambda html, default_url: SimpleNamespace(title="Client Challenge", sitename="Example", date="2025-02-10"),
    )
    monkeypatch.setattr("app.sources.trafilatura.extract", lambda html, url, favor_precision: "A required part of this site couldn't load.")

    source = _source_from_result(
        {"title": "Actual report title", "href": "https://example.org/report", "body": "Useful search summary"},
        "latest report",
    )

    assert source is not None
    assert source["title"] == "Actual report title"
    assert source["content"] == ""
    assert source["excerpt"] == "Useful search summary"
    assert source["published_at"] is None


def test_curly_apostrophe_challenge_text_is_not_saved_as_content(monkeypatch) -> None:
    html = "<html><body>Challenge response</body></html>"
    monkeypatch.setattr("app.sources._fetch_html", lambda url: (html, url))
    monkeypatch.setattr(
        "app.sources.trafilatura.extract_metadata",
        lambda html, default_url: SimpleNamespace(title="Research report", sitename="Example", date=None),
    )
    monkeypatch.setattr("app.sources.trafilatura.extract", lambda html, url, favor_precision: "A required part of this site couldn’t load.")

    source = _source_from_result(
        {"title": "Real search title", "href": "https://example.org/report", "body": "Search result evidence"},
        "recent research",
    )

    assert source is not None
    assert source["content"] == ""
    assert source["excerpt"] == "Search result evidence"


def test_search_results_are_interleaved_across_query_variants(monkeypatch) -> None:
    class DiverseDDGS(FakeDDGS):
        def text(self, query: str, **kwargs: object) -> list[dict[str, object]]:
            type(self).calls.append((query, kwargs))
            label = str(len(type(self).calls))
            return [
                {"title": f"Result {label}-1", "href": f"https://example.org/{label}-1", "body": "Snippet"},
                {"title": f"Result {label}-2", "href": f"https://example.org/{label}-2", "body": "Snippet"},
            ]

    DiverseDDGS.calls = []
    monkeypatch.setattr("app.sources.DDGS", DiverseDDGS)
    monkeypatch.setattr("app.sources._fetch_html", lambda url: None)

    sources = search_web("battery storage", "What changed recently?")

    assert [source["title"] for source in sources] == ["Result 1-1", "Result 2-1", "Result 3-1", "Result 1-2", "Result 2-2", "Result 3-2"]


def test_scraper_rejects_redirects_to_private_destinations(monkeypatch) -> None:
    class FakeResponse:
        status_code = 302
        headers = {"location": "http://127.0.0.1/private"}

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeClient:
        requests: list[str] = []

        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def stream(self, method: str, url: str) -> FakeResponse:
            type(self).requests.append(url)
            return FakeResponse()

    FakeClient.requests = []
    destinations: list[str] = []

    def public_destination(url: str) -> bool:
        destinations.append(url)
        return "127.0.0.1" not in url

    monkeypatch.setattr("app.sources.httpx.Client", FakeClient)
    monkeypatch.setattr("app.sources._is_public_destination", public_destination)

    assert _fetch_html("https://example.org/article") is None
    assert FakeClient.requests == ["https://example.org/article"]
    assert destinations == ["https://example.org/article", "http://127.0.0.1/private"]


def test_search_web_reports_failure_when_provider_cannot_start(monkeypatch) -> None:
    def unavailable_provider(**kwargs: object):
        raise RuntimeError("search engines unavailable")

    monkeypatch.setattr("app.sources.DDGS", unavailable_provider)

    try:
        search_web("energy storage", "What changed recently?")
    except SearchProviderError as error:
        assert "RuntimeError" in str(error)
    else:
        raise AssertionError("Expected a provider error")

def test_search_retries_a_rate_limited_query(monkeypatch):
    """A provider burst-limit must not lose the whole run."""
    attempts = {"count": 0}

    class FakeDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def text(self, query, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("rate limited")
            return [{"title": "Recovered", "href": "https://example.org/a", "body": "text"}]

    monkeypatch.setattr("app.sources.DDGS", FakeDDGS)
    monkeypatch.setattr("app.sources.time.sleep", lambda _: None)
    monkeypatch.setattr("app.sources._fetch_html", lambda url: ("<html></html>", url))
    monkeypatch.setattr("app.sources.trafilatura.extract", lambda *a, **k: "Body text")

    sources = search_web("battery storage", "battery storage limitations")

    assert attempts["count"] >= 2, "the query must be retried"
    assert sources, "the recovered results must still be returned"
