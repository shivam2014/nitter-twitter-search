"""Orchestration: instance fallback, transport choice, result shaping."""

from pathlib import Path

import pytest

import sys

import nitter_search  # noqa: F401  (ensures the submodule is imported)

search_module = sys.modules["nitter_search.search"]
from nitter_search.search import SearchRequest, _dedupe, _sort_newest_first, search
from nitter_search.transport import ChallengeBlocked, TransportError

FIXTURES = Path(__file__).parent / "fixtures"
PROFILE = (FIXTURES / "profile.html").read_text()
SEARCH_PAGE = (FIXTURES / "search.html").read_text()
RSS = (FIXTURES / "user_rss.xml").read_text()
CHALLENGE = "<html><title>Making sure you're not a bot!</title></html>"
RATE_LIMITED = "<html><div class='error-panel'>Instance has no auth tokens, or is fully rate limited.</div></html>"
NO_RESULTS = "<html><div class='error-panel'>No items found</div></html>"


class FakeSession:
    def __init__(self, pages):
        self.pages = list(pages)
        self.urls = []
        self.closed = False

    def fetch(self, url, timeout=None):
        self.urls.append(url)
        if not self.pages:
            raise TransportError("no more pages queued")
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return page

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def no_health_writes(monkeypatch):
    monkeypatch.setattr(search_module.instances_mod, "record_result", lambda *a, **k: None)


def wire(monkeypatch, instances, http=None, session=None):
    monkeypatch.setattr(
        search_module.instances_mod, "candidates", lambda override, limit=5: list(instances)
    )
    if http is not None:
        monkeypatch.setattr(search_module, "http_get", http)
    if session is not None:
        monkeypatch.setattr(search_module, "get_default_session", lambda **kw: session)
        monkeypatch.setattr(search_module, "shutdown_default_session", lambda: session.close())


class TestTransportChoice:
    def test_rss_first_for_plain_requests(self, monkeypatch):
        session = FakeSession([])
        wire(monkeypatch, ["https://a.example"], http=lambda url, timeout=10: RSS, session=session)
        result = search(SearchRequest(user="NASA", limit=5))
        assert result["search_metadata"]["method"] == "rss"
        assert result["search_metadata"]["total"] == 5
        assert session.urls == []

    def test_challenge_falls_back_to_browser(self, monkeypatch):
        session = FakeSession([PROFILE])
        wire(
            monkeypatch,
            ["https://a.example"],
            http=lambda url, timeout=10: CHALLENGE,
            session=session,
        )
        result = search(SearchRequest(user="NASA", limit=5))
        assert result["search_metadata"]["method"] == "browser"
        assert session.urls and "/NASA" in session.urls[0]

    def test_stats_prefers_browser(self, monkeypatch):
        session = FakeSession([SEARCH_PAGE])
        calls = []
        wire(
            monkeypatch,
            ["https://a.example"],
            http=lambda url, timeout=10: calls.append(url) or RSS,
            session=session,
        )
        result = search(SearchRequest(query="mars", limit=5, with_stats=True))
        assert result["search_metadata"]["method"] == "browser"
        assert calls == []
        assert all(tweet["likes"] is not None for tweet in result["tweets"][:5])

    def test_stats_degrades_to_rss_when_browser_fails(self, monkeypatch):
        session = FakeSession([ChallengeBlocked("nope")] * 3)
        wire(
            monkeypatch,
            ["https://a.example"],
            http=lambda url, timeout=10: RSS,
            session=session,
        )
        result = search(SearchRequest(user="NASA", limit=3, with_stats=True))
        assert result["search_metadata"]["method"] == "rss"
        assert result["search_metadata"]["total"] == 3

    def test_no_browser_flag_does_not_launch_one(self, monkeypatch):
        session = FakeSession([PROFILE])
        wire(monkeypatch, ["https://a.example"], http=lambda url, timeout=10: CHALLENGE, session=session)
        result = search(SearchRequest(user="NASA", limit=3, allow_browser=False))
        assert result["tweets"] == []
        assert session.urls == []


class TestFallback:
    def test_rate_limited_instance_is_skipped(self, monkeypatch):
        pages = [RATE_LIMITED, PROFILE]
        session = FakeSession([])
        wire(monkeypatch, ["https://a.example", "https://b.example"], session=session)

        def http(url, timeout=10):
            return pages.pop(0)

        monkeypatch.setattr(search_module, "http_get", http)
        result = search(SearchRequest(user="NASA", limit=3, allow_browser=True))
        tried = result["search_metadata"]["instances_tried"]
        assert "rate limited" in tried[0]["error"].lower()
        assert tried[1]["ok"] is True

    def test_all_instances_failing_is_reported(self, monkeypatch):
        wire(
            monkeypatch,
            ["https://a.example"],
            http=lambda url, timeout=10: (_ for _ in ()).throw(TransportError("refused")),
            session=FakeSession([]),
        )
        result = search(SearchRequest(user="NASA", limit=3))
        assert result["tweets"] == []
        assert "every instance failed" in result["search_metadata"]["error"].lower()

    def test_no_results_is_terminal(self, monkeypatch):
        calls = []

        def http(url, timeout=10):
            calls.append(url)
            return NO_RESULTS

        wire(monkeypatch, ["https://a.example", "https://b.example"], http=http, session=FakeSession([]))
        result = search(SearchRequest(user="NASA", query="zzz", limit=3))
        assert result["tweets"] == []
        assert len(calls) == 1
        assert "no results" in result["search_metadata"]["error"].lower()


class TestValidation:
    def test_missing_target(self):
        result = search(SearchRequest())
        assert "provide a username" in result["search_metadata"]["error"].lower()

    def test_bad_username(self):
        result = search(SearchRequest(user="not a user"))
        assert "username" in result["search_metadata"]["error"].lower()

    def test_bad_date(self):
        result = search(SearchRequest(user="NASA", since="nope"))
        assert "since" in result["search_metadata"]["error"].lower()

    def test_zero_limit_skips_transport(self, monkeypatch):
        session = FakeSession([])
        wire(monkeypatch, ["https://a.example"], http=lambda url, timeout=10: RSS, session=session)
        result = search(SearchRequest(user="NASA", limit=0))
        assert result["tweets"] == []
        assert result["search_metadata"]["method"] == "skipped"
        assert session.urls == []


class TestResultShaping:
    def test_deduplicates_by_id(self):
        tweets = [{"id": "1"}, {"id": "1"}, {"id": "2"}]
        assert len(_dedupe(tweets)) == 2

    def test_sorts_newest_first(self):
        tweets = [{"date": "2026-01-01T00:00:00Z"}, {"date": "2026-02-01T00:00:00Z"}, {"date": None}]
        ordered = _sort_newest_first(tweets)
        assert ordered[0]["date"] == "2026-02-01T00:00:00Z"
        assert ordered[-1]["date"] is None

    def test_limit_is_applied_after_sorting(self, monkeypatch):
        wire(monkeypatch, ["https://a.example"], http=lambda url, timeout=10: PROFILE, session=FakeSession([PROFILE]))
        result = search(SearchRequest(user="NASA", limit=4, with_stats=True))
        dates = [tweet["date"] for tweet in result["tweets"]]
        assert len(dates) == 4
        assert dates == sorted(dates, reverse=True)

    def test_metadata_contract(self, monkeypatch):
        wire(monkeypatch, ["https://a.example"], http=lambda url, timeout=10: RSS, session=FakeSession([]))
        metadata = search(SearchRequest(user="NASA", limit=2))["search_metadata"]
        for key in ("user", "query", "since", "until", "timestamp", "mirror_used", "method", "total", "error"):
            assert key in metadata
        assert metadata["private_profile"] is False

    def test_unknown_instance_is_rejected_cleanly(self):
        result = search(SearchRequest(user="NASA", instances=["https://nitter.net/NASA"]))
        assert "host root" in result["search_metadata"]["error"]
