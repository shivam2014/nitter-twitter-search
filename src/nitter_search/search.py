"""Orchestration: one search call, several instances, cheapest path first."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from . import instances as instances_mod
from .parse import (
    classify_page,
    detect_private,
    parse_html_cursor,
    parse_html_timeline,
    parse_rss_feed,
)
from .transport import (
    BrowserSession,
    ChallengeBlocked,
    TransportError,
    get_default_session,
    http_get,
    shutdown_default_session,
)
from .urls import (
    ValidationError,
    build_profile_url,
    build_search_url,
    normalize_date,
    normalize_instance,
    normalize_username,
)

MAX_PAGES = 5


class NoResults(TransportError):
    """The instance answered definitively: nothing matches the request."""


@dataclass
class SearchRequest:
    """Everything needed to run one search."""

    user: Optional[str] = None
    query: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int = 20
    filters: List[str] = field(default_factory=list)
    min_faves: Optional[int] = None
    min_retweets: Optional[int] = None
    min_replies: Optional[int] = None
    instances: Optional[Iterable[str]] = None
    with_stats: bool = False
    allow_browser: bool = True
    include_replies: bool = True
    timeout: float = 90.0
    browser: Optional[BrowserSession] = None

    def validate(self) -> "SearchRequest":
        self.user = normalize_username(self.user)
        self.query = (self.query or "").strip() or None
        if not self.user and not self.query:
            raise ValidationError("Provide a username, a query, or both")
        self.since = normalize_date(self.since, "since")
        self.until = normalize_date(self.until, "until")
        if self.since and self.until and self.since > self.until:
            raise ValidationError(f"since ({self.since}) is after until ({self.until})")
        if self.limit is None:
            self.limit = 20
        self.limit = max(0, int(self.limit))
        return self


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _envelope(request: SearchRequest, **extra: Any) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "user": request.user,
        "query": request.query,
        "since": request.since,
        "until": request.until,
        "limit": request.limit,
        "private_profile": False,
        "timestamp": _now(),
        "mirror_used": None,
        "method": None,
        "total": 0,
        "error": None,
        "instances_tried": [],
    }
    metadata.update(extra)
    return {"search_metadata": metadata, "tweets": []}


def _dedupe(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for tweet in tweets:
        key = tweet.get("id") or tweet.get("url") or tweet.get("text", "")[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(tweet)
    return unique


def _matches_query(tweet: Any, query: Optional[str]) -> bool:
    """True when every meaningful token of ``query`` appears in the tweet text.

    Some mirrors answer a search URL with an unfiltered timeline when their
    backend tokens are missing. Verifying locally costs nothing and stops
    unrelated tweets from being returned as search results.
    """
    if not query:
        return True
    tokens = [token.strip('"').lower() for token in query.split()]
    tokens = [token for token in tokens if len(token) > 1]
    if not tokens:
        return True
    raw = tweet.get("text") if isinstance(tweet, dict) else tweet
    haystack = str(raw or "").lower()
    return all(token in haystack for token in tokens)


def _sort_newest_first(tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Order by ISO timestamp, newest first; undated tweets sink to the end."""
    return sorted(tweets, key=lambda tweet: tweet.get("date") or "", reverse=True)


def _url_for(
    request: SearchRequest, instance: str, rss: bool, cursor: Optional[str] = None
) -> str:
    if request.user and not request.query:
        return build_profile_url(instance, request.user, rss=rss, cursor=cursor)
    return build_search_url(
        instance,
        user=request.user,
        query=request.query,
        since=request.since,
        until=request.until,
        filters=request.filters,
        min_faves=request.min_faves,
        min_retweets=request.min_retweets,
        min_replies=request.min_replies,
        cursor=cursor,
        rss=rss,
    )


def _fetch_rss(request: SearchRequest, instance: str) -> List[Dict[str, Any]]:
    payload = http_get(_url_for(request, instance, rss=True), timeout=15)
    state = classify_page(payload)
    if state == "challenge":
        raise ChallengeBlocked("RSS endpoint is challenge-gated")
    if state == "ratelimited":
        raise TransportError("Instance is rate limited")
    if state == "disabled":
        raise TransportError("Search is disabled on this instance")
    if state == "missing":
        raise NoResults("Account not found on this instance")
    if state == "empty":
        raise TransportError("Instance returned no items")
    if state == "protected":
        raise NoResults("Account is protected")
    return parse_rss_feed(payload, instance)


def _fetch_browser(
    request: SearchRequest, instance: str, session: BrowserSession
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    for page_number in range(MAX_PAGES):
        url = _url_for(request, instance, rss=False, cursor=cursor)
        payload = session.fetch(url)
        state = classify_page(payload)
        if state == "ratelimited":
            raise TransportError("Instance is rate limited")
        if state == "disabled":
            raise TransportError("Search is disabled on this instance")
        if page_number == 0 and state == "missing":
            raise NoResults("Account not found on this instance")
        if page_number == 0 and state == "protected":
            raise NoResults("Account is protected")
        if page_number == 0 and state == "empty":
            raise TransportError("Instance returned no items")
        page_tweets = parse_html_timeline(
            payload, instance, include_replies=request.include_replies
        )
        collected.extend(page_tweets)
        if len(collected) >= request.limit or not page_tweets:
            break
        cursor = parse_html_cursor(payload)
        if not cursor:
            break
    return collected


def _attempt(
    request: SearchRequest, instance: str, session: BrowserSession
) -> tuple[List[Dict[str, Any]], str]:
    """Try one instance over both transports. Returns (tweets, method).

    With ``with_stats`` the browser goes first because only rendered HTML
    carries engagement counts; the feed is still tried afterwards so a
    challenge-gated instance degrades to fewer fields instead of no results.
    """
    problems: List[str] = []
    # RSS "search" is only implemented on some forks, and the ones that do
    # implement it sometimes return an unfiltered timeline. Ask for rendered
    # pages whenever there is a query; timelines stay on the cheap path.
    wants_browser = request.with_stats or bool(request.query)
    order = ["browser", "rss"] if wants_browser else ["rss", "browser"]

    for transport in order:
        if transport == "browser":
            if not request.allow_browser:
                continue
            try:
                return _fetch_browser(request, instance, session), "browser"
            except NoResults:
                raise
            except ChallengeBlocked as exc:
                problems.append(f"browser challenge: {exc}")
            except TransportError as exc:
                problems.append(f"browser: {exc}")
            except Exception as exc:
                problems.append(f"browser error: {exc}")
        else:
            if request.with_stats and request.limit > 20:
                continue  # the feed only ever holds one page
            try:
                return _fetch_rss(request, instance), "rss"
            except NoResults:
                raise
            except ChallengeBlocked as exc:
                problems.append(f"rss challenge: {exc}")
            except TransportError as exc:
                problems.append(f"rss: {exc}")
            except Exception as exc:
                problems.append(f"rss parse: {exc}")

    raise TransportError("; ".join(problems) or "no transport available")


def search(request: SearchRequest) -> Dict[str, Any]:
    """Run a search, falling back across instances until one answers."""
    try:
        request.validate()
    except ValidationError as exc:
        return _envelope(request, error=str(exc))

    if request.limit == 0:
        return _envelope(request, method="skipped")

    envelope = _envelope(request)
    metadata = envelope["search_metadata"]
    tried: List[Dict[str, Any]] = metadata["instances_tried"]

    try:
        targets = instances_mod.candidates(request.instances, limit=5)
    except ValidationError as exc:
        metadata["error"] = str(exc)
        return envelope

    deadline = time.monotonic() + request.timeout
    collected: List[Dict[str, Any]] = []
    definitive: Optional[str] = None
    session = request.browser
    owns_session = session is None
    if session is None:
        session = get_default_session()

    for instance in targets:
        if time.monotonic() > deadline:
            tried.append({"url": instance, "ok": False, "error": "deadline exceeded"})
            break
        record: Dict[str, Any] = {"url": instance, "ok": False, "method": None, "error": None}
        tried.append(record)
        try:
            tweets, method = _attempt(request, instance, session)
        except NoResults as exc:
            record["error"] = str(exc)
            definitive = (
                "The instance returned no results. Check the username, the query, "
                "or widen the date range."
            )
            break
        except TransportError as exc:
            record["error"] = str(exc)
            instances_mod.record_result(instance, False)
            continue
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            instances_mod.record_result(instance, False)
            continue

        record.update(ok=True, method=method)
        instances_mod.record_result(instance, True)
        collected.extend(tweets)
        if tweets:
            break
        definitive = definitive or "No tweets found for that request."

    if owns_session:
        # A CLI call owns its browser; the MCP server keeps its own alive.
        shutdown_default_session()

    if not collected:
        metadata["error"] = definitive or (
            "Every instance failed. Run `nitter-search --check` to see which are reachable."
        )
        return envelope

    tweets = _sort_newest_first(_dedupe(collected))
    if request.query:
        tweets = [tweet for tweet in tweets if _matches_query(tweet, request.query)]
    tweets = tweets[: request.limit]
    metadata.update(
        mirror_used=tried[-1]["url"],
        method=tried[-1]["method"],
        total=len(tweets),
    )
    envelope["tweets"] = tweets
    return envelope


def scrape(
    username: Optional[str] = None,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_tweets: int = 100,
    mirror: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Backwards-compatible wrapper around :func:`search`."""
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


def detect_login_wall(html: str, username: Optional[str] = None) -> bool:
    """Public helper kept for callers that only have a page body."""
    return detect_private(html, username)
