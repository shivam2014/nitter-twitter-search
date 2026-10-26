"""Backwards-compatible entry points.

Older versions of this package exposed ``scrape_user_tweets_camoufox`` and
``parse_tweets_from_html`` from this module. They are kept as thin wrappers so
existing callers and skills keep working, but the implementation now lives in
:mod:`nitter_search.search`, :mod:`nitter_search.transport` and
:mod:`nitter_search.parse`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .parse import (
    classify_page,
    count_to_int,
    detect_private,
    parse_html_timeline,
    parse_timestamp,
)
from .search import SearchRequest, search
from .transport import BrowserSession, TransportError


def scrape_user_tweets_camoufox(
    username: Optional[str],
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_tweets: int = 100,
    mirror: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Fetch tweets for ``username`` using the cheapest transport available.

    Returns the same ``{"search_metadata": ..., "tweets": [...]}`` envelope as
    previous versions. ``mirror`` pins a single instance; omit it to let the
    package pick a healthy one.
    """
    request = SearchRequest(
        user=username,
        query=query,
        since=start_date,
        until=end_date,
        limit=max_tweets,
        instances=[mirror] if mirror else None,
        **kwargs,
    )
    return search(request)


def parse_tweets_from_html(
    html: str,
    query: Optional[str] = None,
    max_tweets: int = 100,
    instance: str = "https://nitter.net",
) -> List[Dict[str, Any]]:
    """Parse tweets out of a saved Nitter page, filtered by ``query``."""
    tweets = parse_html_timeline(html, instance)
    if query and query.strip():
        needle = query.strip().lower()
        tweets = [tweet for tweet in tweets if needle in tweet.get("text", "").lower()]
    return tweets[:max_tweets]


def camoufox_available() -> bool:
    """True when the optional Camoufox dependency can be imported."""
    return BrowserSession().available


__all__ = [
    "BrowserSession",
    "TransportError",
    "camoufox_available",
    "classify_page",
    "count_to_int",
    "detect_private",
    "parse_html_timeline",
    "parse_timestamp",
    "parse_tweets_from_html",
    "scrape_user_tweets_camoufox",
]
