"""URL construction and input validation for Nitter requests.

Nitter exposes the same filter vocabulary as Twitter's advanced search, but
passes it through URL parameters instead of a query language:

    /<user>/search?f=tweets&q=<text>&since=YYYY-MM-DD&until=YYYY-MM-DD

Adding ``/rss`` before the query string returns the same result set as an RSS
feed, which avoids the anti-bot challenge most public instances put in front of
their HTML pages.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable, Optional
from urllib.parse import urlencode, urlparse

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
STATUS_ID_RE = re.compile(r"/status/(\d+)")

#: Filters Nitter accepts verbatim in the query string.
SUPPORTED_FILTERS = ("media", "links", "quotes", "replies", "nativeretweets")


class ValidationError(ValueError):
    """Raised when caller input cannot be turned into a Nitter request."""


def normalize_instance(instance: str) -> str:
    """Return ``instance`` as a bare ``scheme://host[:port]`` base URL."""
    if not instance or not str(instance).strip():
        raise ValidationError("Instance URL is empty")
    text = str(instance).strip().rstrip("/")
    if "://" not in text:
        text = f"https://{text}"
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(f"Unsupported instance scheme: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValidationError(f"Instance URL has no host: {instance!r}")
    if parsed.path not in ("", "/"):
        # Instances live at the root; a path here is almost always a mistake.
        raise ValidationError(
            f"Instance URL must be a host root, got path {parsed.path!r}"
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def normalize_username(user: Optional[str]) -> Optional[str]:
    """Validate and strip a Twitter handle. Returns ``None`` for empty input."""
    if user is None:
        return None
    handle = str(user).strip().lstrip("@")
    if not handle:
        return None
    if not USERNAME_RE.match(handle):
        raise ValidationError(
            "Username must be 1-15 characters of letters, digits or underscore"
        )
    return handle


def normalize_date(value: Optional[str], name: str) -> Optional[str]:
    """Validate ``YYYY-MM-DD`` input and return it unchanged."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError(f"{name} must be YYYY-MM-DD, got {value!r}") from exc
    if parsed.year < 2006:
        # Twitter's first tweet is from 2006; earlier dates return nothing.
        raise ValidationError(f"{name} is before Twitter existed: {value!r}")
    if parsed > date.today():
        raise ValidationError(f"{name} is in the future: {value!r}")
    return parsed.isoformat()


def normalize_filters(filters: Optional[Iterable[str]]) -> list[str]:
    """Validate ``filter=`` values accepted by Nitter."""
    if not filters:
        return []
    if isinstance(filters, str):
        filters = [filters]
    seen: list[str] = []
    for raw in filters:
        value = str(raw).strip().lower()
        if not value:
            continue
        if value not in SUPPORTED_FILTERS:
            raise ValidationError(
                f"Unsupported filter {raw!r}. Choose from: {', '.join(SUPPORTED_FILTERS)}"
            )
        if value not in seen:
            seen.append(value)
    return seen


def _query_params(
    query: Optional[str],
    since: Optional[str],
    until: Optional[str],
    filters: Optional[Iterable[str]],
    min_faves: Optional[int],
    min_retweets: Optional[int],
    min_replies: Optional[int],
    cursor: Optional[str],
    tweets_only: bool,
) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    if tweets_only:
        params.append(("f", "tweets"))
    params.append(("q", (query or "").strip()))
    if since:
        params.append(("since", since))
    if until:
        params.append(("until", until))
    for name, value in (
        ("min_faves", min_faves),
        ("min_retweets", min_retweets),
        ("min_replies", min_replies),
    ):
        if value is not None:
            if int(value) < 0:
                raise ValidationError(f"{name} cannot be negative")
            params.append((name, str(int(value))))
    for value in normalize_filters(filters):
        params.append(("filter", value))
    if cursor:
        params.append(("cursor", cursor))
    return params


def build_search_url(
    instance: str,
    user: Optional[str] = None,
    query: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    filters: Optional[Iterable[str]] = None,
    min_faves: Optional[int] = None,
    min_retweets: Optional[int] = None,
    min_replies: Optional[int] = None,
    cursor: Optional[str] = None,
    rss: bool = False,
) -> str:
    """Build a Nitter search URL, scoped to a user when ``user`` is given."""
    base = normalize_instance(instance)
    handle = normalize_username(user)
    since = normalize_date(since, "since")
    until = normalize_date(until, "until")
    if since and until and since > until:
        raise ValidationError(f"since ({since}) is after until ({until})")

    path = f"/{handle}/search" if handle else "/search"
    feed = "rss" if rss else "html"
    if feed == "rss":
        path = f"{path}/rss"
    params = _query_params(
        query, since, until, filters, min_faves, min_retweets, min_replies, cursor, True
    )
    return f"{base}{path}?{urlencode(params)}"


def build_profile_url(
    instance: str, user: str, rss: bool = False, cursor: Optional[str] = None
) -> str:
    """Build a user timeline URL (``/<user>`` or ``/<user>/rss``)."""
    base = normalize_instance(instance)
    handle = normalize_username(user)
    if not handle:
        raise ValidationError("A username is required")
    url = f"{base}/{handle}" + ("/rss" if rss else "")
    if cursor:
        url = f"{url}?{urlencode({'cursor': cursor})}"
    return url


def build_cursor_url(instance: str, cursor_href: str) -> str:
    """Resolve a ``show-more`` cursor link against an instance."""
    base = normalize_instance(instance)
    if cursor_href.startswith("http://") or cursor_href.startswith("https://"):
        return cursor_href
    if not cursor_href.startswith("/"):
        cursor_href = f"/{cursor_href}"
    return f"{base}{cursor_href}"


def extract_status_id(url: Optional[str]) -> Optional[str]:
    """Pull the numeric status id out of a tweet URL."""
    if not url:
        return None
    match = STATUS_ID_RE.search(url)
    return match.group(1) if match else None


def rewrite_host(url: Optional[str], instance: str) -> Optional[str]:
    """Repoint a URL returned by an instance at the instance that served it.

    Nitter feeds emit absolute links using the instance's configured public
    host, which is frequently a different domain than the one actually serving
    the request.
    """
    if not url:
        return None
    base = normalize_instance(instance)
    parsed = urlparse(url)
    if not parsed.netloc:
        return f"{base}{url if url.startswith('/') else '/' + url}"
    suffix = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{base}{parsed.path}{suffix}{fragment}"
