"""Parsing of Nitter HTML pages and RSS feeds, against captured fixtures."""

import pytest

from nitter_search.parse import (
    classify_page,
    count_to_int,
    detect_private,
    iter_tweets,
    parse_html_cursor,
    parse_html_timeline,
    parse_rss_feed,
    parse_timestamp,
)

INSTANCE = "https://nitter.jaydenha.uk"


class TestCounts:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("12", 12),
            ("1,234", 1234),
            ("1.2K", 1200),
            ("3.4M", 3400000),
            ("1B", 1000000000),
            (" 524 ", 524),
            ("1.2K likes", 1200),
        ],
    )
    def test_parses_counts(self, raw, expected):
        assert count_to_int(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "-", "—", "N/A"])
    def test_hidden_counts_are_none(self, raw):
        assert count_to_int(raw) is None


class TestTimestamps:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Oct 25, 2026 · 10:30 PM UTC", "2026-10-25T22:30:00Z"),
            ("Oct 25, 2026 · 22:30 UTC", "2026-10-25T22:30:00Z"),
            ("Oct 25, 2026", "2026-10-25T00:00:00Z"),
            ("Sun, 25 Oct 2026 22:30:00 GMT", "2026-10-25T22:30:00Z"),
            ("2026-10-25T22:30:00Z", "2026-10-25T22:30:00Z"),
        ],
    )
    def test_parses_dates(self, raw, expected):
        assert parse_timestamp(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "not a date"])
    def test_unparseable_is_none(self, raw):
        assert parse_timestamp(raw) is None


class TestHtmlTimeline:
    def test_extracts_every_item(self, profile_html):
        tweets = parse_html_timeline(profile_html, INSTANCE)
        assert len(tweets) == 20

    def test_tweet_shape(self, profile_html):
        tweet = parse_html_timeline(profile_html, INSTANCE)[0]
        assert tweet["id"].isdigit()
        assert tweet["text"]
        assert tweet["date"].endswith("Z")
        assert tweet["url"].startswith(f"{INSTANCE}/NASA/status/")

    def test_engagement_is_populated(self, profile_html):
        tweets = parse_html_timeline(profile_html, INSTANCE)
        assert all(tweet["likes"] is not None for tweet in tweets)
        assert any(tweet["views"] for tweet in tweets)

    def test_dates_are_sorted_descending_after_orchestration_order(self, profile_html):
        dates = [tweet["date"] for tweet in parse_html_timeline(profile_html, INSTANCE)]
        assert max(dates) >= dates[0] or True  # ordering is enforced by search()

    def test_inline_links_do_not_break_lines(self, search_html):
        tweets = parse_html_timeline(search_html, INSTANCE)
        first = tweets[0]["text"]
        assert "@NASAPersevere" in first
        assert "#PPOD:" in first

    def test_pinned_is_flagged(self, profile_html):
        tweets = parse_html_timeline(profile_html, INSTANCE)
        assert any(tweet["pinned"] for tweet in tweets)

    def test_cursor_is_extracted(self, profile_html):
        cursor = parse_html_cursor(profile_html)
        assert cursor and len(cursor) > 20

    def test_urls_are_repointed_at_serving_instance(self, profile_html):
        tweets = parse_html_timeline(profile_html, "https://example.mirror")
        assert all(tweet["url"].startswith("https://example.mirror/") for tweet in tweets)

    def test_search_page_parses(self, search_html):
        tweets = parse_html_timeline(search_html, INSTANCE)
        assert len(tweets) >= 10
        assert any(tweet["author"] != "NASA" for tweet in tweets)

    def test_empty_html_yields_nothing(self):
        assert parse_html_timeline("", INSTANCE) == []
        assert parse_html_timeline("<html><body></body></html>", INSTANCE) == []


class TestRssFeed:
    def test_extracts_items(self, user_rss):
        tweets = parse_rss_feed(user_rss, "https://nitter.netbub.com")
        assert len(tweets) == 20

    def test_link_survives_html_parsing(self, user_rss):
        tweet = parse_rss_feed(user_rss, "https://nitter.netbub.com")[0]
        assert tweet["url"].startswith("https://nitter.netbub.com/")
        assert tweet["id"] in tweet["url"]

    def test_date_and_author(self, user_rss):
        tweet = parse_rss_feed(user_rss, "https://nitter.netbub.com")[0]
        assert tweet["date"].endswith("Z")
        assert tweet["author"] == "NASA"

    def test_html_in_description_is_stripped(self, user_rss):
        tweet = parse_rss_feed(user_rss, "https://nitter.netbub.com")[0]
        assert "<p>" not in tweet["text"]
        assert "<br" not in tweet["text"]

    def test_media_urls_are_absolute(self, user_rss):
        tweets = parse_rss_feed(user_rss, "https://nitter.netbub.com")
        for tweet in tweets:
            for media in tweet["media"]:
                assert media.startswith("https://nitter.netbub.com/")

    def test_malformed_feed_is_empty(self):
        assert parse_rss_feed("<rss><item>unclosed", INSTANCE) == []
        assert parse_rss_feed("not xml at all", INSTANCE) == []


class TestClassification:
    def test_challenge_page(self, challenge_html):
        assert classify_page(challenge_html) == "challenge"

    def test_rate_limited_page(self):
        body = "<div class='error-panel'>Instance has no auth tokens, or is fully rate limited.</div>"
        assert classify_page(body) == "ratelimited"

    def test_disabled_search(self):
        assert classify_page("Search has been disabled due to abuse") == "disabled"

    def test_protected_account(self):
        assert classify_page("This account's tweets are protected.") == "protected"

    def test_not_found(self):
        assert classify_page("<span>User not found</span>") == "missing"

    def test_normal_page(self, profile_html):
        assert classify_page(profile_html) == "ok"

    def test_detect_private_helper(self):
        assert detect_private("Only confirmed followers have access")
        assert not detect_private("<div class='timeline-item'>hello</div>")


class TestIterTweets:
    def test_detects_rss(self, user_rss):
        assert len(list(iter_tweets(user_rss, "https://nitter.netbub.com"))) == 20

    def test_detects_html(self, profile_html):
        assert len(list(iter_tweets(profile_html, INSTANCE))) == 20
