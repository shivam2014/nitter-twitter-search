"""URL building and input validation."""

import pytest

from nitter_search.urls import (
    ValidationError,
    build_profile_url,
    build_search_url,
    extract_status_id,
    normalize_date,
    normalize_filters,
    normalize_instance,
    normalize_username,
    rewrite_host,
)

INSTANCE = "https://nitter.netbub.com"


class TestInstanceNormalisation:
    def test_adds_https(self):
        assert normalize_instance("nitter.netbub.com") == INSTANCE

    def test_strips_trailing_slash(self):
        assert normalize_instance("https://nitter.netbub.com/") == INSTANCE

    def test_keeps_port(self):
        assert normalize_instance("http://localhost:8080") == "http://localhost:8080"

    @pytest.mark.parametrize("bad", ["", "   ", None])
    def test_rejects_empty(self, bad):
        with pytest.raises(ValidationError):
            normalize_instance(bad)

    def test_rejects_path(self):
        with pytest.raises(ValidationError):
            normalize_instance("https://nitter.netbub.com/NASA")

    def test_rejects_scheme(self):
        with pytest.raises(ValidationError):
            normalize_instance("ftp://nitter.netbub.com")


class TestUsername:
    def test_strips_at(self):
        assert normalize_username("@NASA") == "NASA"

    def test_empty_is_none(self):
        assert normalize_username("") is None
        assert normalize_username(None) is None

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            normalize_username("a" * 16)

    def test_rejects_spaces(self):
        with pytest.raises(ValidationError):
            normalize_username("not a user")

    def test_allows_underscore_and_digits(self):
        assert normalize_username("user_2026") == "user_2026"


class TestDates:
    def test_valid(self):
        assert normalize_date("2026-10-01", "since") == "2026-10-01"

    def test_empty_is_none(self):
        assert normalize_date("", "since") is None
        assert normalize_date(None, "since") is None

    @pytest.mark.parametrize("bad", ["10-01-2026", "2026-13-01", "yesterday"])
    def test_rejects_malformed(self, bad):
        with pytest.raises(ValidationError):
            normalize_date(bad, "since")

    def test_rejects_future(self):
        with pytest.raises(ValidationError):
            normalize_date("2999-01-01", "until")

    def test_rejects_pre_twitter(self):
        with pytest.raises(ValidationError):
            normalize_date("1999-01-01", "since")


class TestSearchUrl:
    def test_user_search(self):
        url = build_search_url(INSTANCE, user="NASA", query="mars")
        assert url == f"{INSTANCE}/NASA/search?f=tweets&q=mars"

    def test_global_search_has_no_user_segment(self):
        url = build_search_url(INSTANCE, query="mars rover")
        assert url.startswith(f"{INSTANCE}/search?f=tweets&q=mars+rover")

    def test_dates_become_server_side_filters(self):
        url = build_search_url(INSTANCE, user="NASA", since="2026-10-01", until="2026-10-26")
        assert "since=2026-10-01" in url
        assert "until=2026-10-26" in url

    def test_date_order_is_validated(self):
        with pytest.raises(ValidationError):
            build_search_url(INSTANCE, user="NASA", since="2026-10-26", until="2026-10-01")

    def test_engagement_filters(self):
        url = build_search_url(INSTANCE, user="NASA", min_faves=100, min_retweets=10)
        assert "min_faves=100" in url
        assert "min_retweets=10" in url

    def test_negative_filter_rejected(self):
        with pytest.raises(ValidationError):
            build_search_url(INSTANCE, user="NASA", min_faves=-5)

    def test_rss_variant(self):
        url = build_search_url(INSTANCE, user="NASA", query="mars", rss=True)
        assert url.startswith(f"{INSTANCE}/NASA/search/rss?")

    def test_cursor_is_encoded(self):
        cursor = "DAABCgABG/abc+def=="
        url = build_search_url(INSTANCE, user="NASA", cursor=cursor)
        assert "cursor=DAABCgABG%2Fabc%2Bdef%3D%3D" in url

    def test_query_is_encoded(self):
        url = build_search_url(INSTANCE, query="c++ & rust")
        assert "c%2B%2B" in url and "%26" in url


class TestProfileUrl:
    def test_html(self):
        assert build_profile_url(INSTANCE, "NASA") == f"{INSTANCE}/NASA"

    def test_rss(self):
        assert build_profile_url(INSTANCE, "NASA", rss=True) == f"{INSTANCE}/NASA/rss"

    def test_cursor(self):
        assert build_profile_url(INSTANCE, "NASA", cursor="abc") == f"{INSTANCE}/NASA?cursor=abc"

    def test_requires_user(self):
        with pytest.raises(ValidationError):
            build_profile_url(INSTANCE, "")


class TestFilters:
    def test_normalises(self):
        assert normalize_filters(["Media", " LINKS "]) == ["media", "links"]

    def test_deduplicates(self):
        assert normalize_filters(["media", "media"]) == ["media"]

    def test_rejects_unknown(self):
        with pytest.raises(ValidationError):
            normalize_filters(["nonsense"])

    def test_string_input(self):
        assert normalize_filters("media") == ["media"]


class TestHelpers:
    def test_extract_status_id(self):
        assert extract_status_id("https://x.com/NASA/status/12345#m") == "12345"

    def test_extract_status_id_missing(self):
        assert extract_status_id("https://x.com/NASA") is None

    def test_rewrite_host_repoints(self):
        url = rewrite_host("http://nitter.meowing.monster/NASA/status/1#m", INSTANCE)
        assert url == f"{INSTANCE}/NASA/status/1#m"

    def test_rewrite_host_relative(self):
        assert rewrite_host("/NASA/status/1", INSTANCE) == f"{INSTANCE}/NASA/status/1"

    def test_rewrite_host_none(self):
        assert rewrite_host(None, INSTANCE) is None
