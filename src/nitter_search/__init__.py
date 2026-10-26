"""Search Twitter/X through Nitter mirrors, with automatic instance fallback.

Quick start::

    from nitter_search import search_tweets

    result = search_tweets(user="NASA", limit=10)
    for tweet in result["tweets"]:
        print(tweet["date"], tweet["text"])
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .instances import check_all, discover, probe
from .parse import count_to_int, parse_timestamp
from .search import SearchRequest, scrape, search
from .transport import BrowserSession, TransportError
from .urls import build_profile_url, build_search_url

__version__ = "2.0.0"

__all__ = [
    "BrowserSession",
    "SearchRequest",
    "TransportError",
    "__version__",
    "build_profile_url",
    "build_search_url",
    "check_all",
    "count_to_int",
    "discover",
    "parse_timestamp",
    "probe",
    "scrape",
    "search",
    "search_tweets",
]


def search_tweets(
    user: Optional[str] = None,
    query: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 20,
    with_stats: bool = False,
    instance: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Search tweets and return ``{"search_metadata": ..., "tweets": [...]}``.

    Args:
        user: Twitter username without ``@``. Omit to search globally.
        query: Search text. Omit to get the plain timeline.
        since: Earliest date, ``YYYY-MM-DD``.
        until: Latest date, ``YYYY-MM-DD``.
        limit: Maximum tweets to return.
        with_stats: Use a browser so like/reply/retweet counts are populated.
        instance: Pin a single Nitter instance instead of auto-selecting.

    Extra keyword arguments are forwarded to :class:`SearchRequest`, so
    ``filters``, ``min_faves``, ``include_replies`` and ``timeout`` all work.
    """
    request = SearchRequest(
        user=user,
        query=query,
        since=since,
        until=until,
        limit=limit,
        with_stats=with_stats,
        instances=[instance] if instance else None,
        **kwargs,
    )
    return search(request)
