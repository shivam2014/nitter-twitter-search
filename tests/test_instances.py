"""Instance discovery, health memory and probing."""

import json

import pytest

from nitter_search import instances
from nitter_search.instances import (
    HEALTH_TTL,
    cache_file,
    candidates,
    discover,
    health_file,
    probe,
    record_result,
)

STATUS_PAYLOAD = {
    "hosts": [
        {
            "url": "https://slow.example",
            "healthy": True,
            "rss": True,
            "points": 10,
            "is_bad_host": False,
        },
        {
            "url": "https://fast.example",
            "healthy": True,
            "rss": True,
            "points": 80,
            "is_bad_host": False,
        },
        {
            "url": "https://dead.example",
            "healthy": False,
            "rss": False,
            "points": 99,
            "is_bad_host": False,
        },
        {
            "url": "https://banned.example",
            "healthy": True,
            "rss": True,
            "points": 100,
            "is_bad_host": True,
        },
        {
            "url": "nitter.net",
            "healthy": True,
            "rss": True,
            "points": 500,
            "is_bad_host": False,
        },
    ]
}


@pytest.fixture
def status(monkeypatch):
    monkeypatch.setattr(instances, "fetch_status", lambda timeout=8.0: STATUS_PAYLOAD["hosts"])
    return STATUS_PAYLOAD


class TestDiscover:
    def test_orders_by_points(self, status):
        urls = [record["url"] for record in discover(force=True)]
        assert urls.index("https://fast.example") < urls.index("https://slow.example")

    def test_drops_unhealthy_and_bad_hosts(self, status):
        urls = {record["url"] for record in discover(force=True)}
        assert "https://dead.example" not in urls
        assert "https://banned.example" not in urls

    def test_drops_known_dead_domains(self, status):
        urls = {record["url"] for record in discover(force=True)}
        assert "https://nitter.net" not in urls

    def test_caches_result(self, status, monkeypatch):
        discover(force=True)
        assert cache_file().exists()
        calls = []
        monkeypatch.setattr(
            instances, "fetch_status", lambda timeout=8.0: calls.append(1) or []
        )
        discover()
        assert calls == []

    def test_falls_back_to_seeds(self, monkeypatch):
        monkeypatch.setattr(instances, "fetch_status", lambda timeout=8.0: [])
        urls = [record["url"] for record in discover(force=True)]
        assert instances.SEED_INSTANCES[0] in urls

    def test_include_unknown_keeps_unhealthy(self, status):
        urls = {record["url"] for record in discover(force=True, include_unknown=True)}
        assert "https://dead.example" in urls


class TestHealth:
    def test_failure_is_remembered(self, status):
        discover(force=True)
        record_result("https://fast.example", False)
        state = json.loads(health_file().read_text())
        assert state["https://fast.example"]["failures"] == 1

    def test_recent_failure_sinks_in_order(self, status):
        discover(force=True)
        record_result("https://fast.example", False)
        urls = [record["url"] for record in discover()]
        assert urls.index("https://slow.example") < urls.index("https://fast.example")

    def test_success_clears_failures(self, status):
        discover(force=True)
        record_result("https://fast.example", False)
        record_result("https://fast.example", True)
        state = json.loads(health_file().read_text())
        assert state["https://fast.example"]["failures"] == 0

    def test_ttl_constant_is_sane(self):
        assert 0 < HEALTH_TTL <= 24 * 60 * 60

    def test_invalid_instance_is_ignored(self):
        record_result("not a url", False)  # must not raise


class TestCandidates:
    def test_override_wins(self):
        assert candidates(["https://only.example"]) == ["https://only.example"]

    def test_override_is_deduplicated(self):
        assert candidates(["only.example", "https://only.example"]) == ["https://only.example"]

    def test_limit_applies(self, status):
        assert len(candidates(limit=1)) == 1


class TestProbe:
    def test_ok_when_feed_has_items(self, monkeypatch):
        monkeypatch.setattr(instances, "_http_get", lambda url, timeout=8.0: "<rss><item>x</item></rss>")
        result = probe("https://fast.example")
        assert result["ok"] and result["rss"] and not result["challenge"]

    def test_challenge_detected(self, monkeypatch):
        monkeypatch.setattr(
            instances, "_http_get", lambda url, timeout=8.0: "Making sure you're not a bot!"
        )
        result = probe("https://fast.example")
        assert result["challenge"] and not result["ok"]

    def test_network_error_is_reported(self, monkeypatch):
        def boom(url, timeout=8.0):
            raise OSError("connection refused")

        monkeypatch.setattr(instances, "_http_get", boom)
        result = probe("https://fast.example")
        assert not result["ok"]
        assert "refused" in result["detail"]
