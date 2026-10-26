"""Parsing of Nitter HTML pages and RSS feeds into plain tweet records."""

from __future__ import annotations

import html as html_module
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .urls import extract_status_id, rewrite_host

#: Snippets that mean an anti-bot challenge page was served instead of content.
CHALLENGE_MARKERS = (
    "making sure you're not a bot",
    "making sure you&#39;re not a bot",
    "anubis",
    "gandalf",
    "checking your browser",
    "just a moment",
    "cf-browser-verification",
    "ddos-guard",
    "please wait while we verify",
)

#: Snippets that mean the instance answered, but with a refusal.
DISABLED_MARKERS = (
    "search disabled",
    "search has been disabled",
    "search is disabled",
)

RATE_LIMIT_MARKERS = (
    "instance has no auth tokens",
    "fully rate limited",
    "rate limited",
    "rate-limited",
)

NOT_FOUND_MARKERS = (
    "user not found",
    "no items found",
    "no results",
    "account doesn't exist",
    "this account doesn",
)

PROTECTED_MARKERS = (
    "tweets are protected",
    "only confirmed followers",
    "protected account",
)

_COUNT_RE = re.compile(r"([\d.,]+)\s*([KMB])?", re.IGNORECASE)
_COUNT_SUFFIX = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def count_to_int(raw: Optional[str]) -> Optional[int]:
    """Convert a Nitter engagement label into an integer.

    ``"1.2K"`` becomes ``1200``, ``"3.4M"`` becomes ``3400000``, ``""`` becomes
    ``None``. Nitter prints ``-`` or nothing at all when a count is hidden.
    """
    if raw is None:
        return None
    text = str(raw).strip().replace("\u00a0", " ")
    if not text or text in {"-", "—", "N/A"}:
        return None
    match = _COUNT_RE.search(text)
    if not match:
        return None
    number, suffix = match.group(1), (match.group(2) or "").upper()
    # Nitter uses "," as a thousands separator and "." as a decimal point.
    cleaned = number.replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if suffix:
        value *= _COUNT_SUFFIX[suffix]
    return int(round(value))


def parse_timestamp(raw: Optional[str]) -> Optional[str]:
    """Normalise a Nitter date (``Oct 25, 2026 · 10:30 PM UTC``) to ISO 8601."""
    if not raw:
        return None
    text = str(raw).strip()
    candidates = [
        "%b %d, %Y · %I:%M %p %Z",
        "%b %d, %Y · %H:%M %Z",
        "%b %d, %Y · %I:%M %p",
        "%b %d, %Y",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    normalised = text.replace("\u00a0", " ").replace("  ", " ")
    for fmt in candidates:
        try:
            parsed = datetime.strptime(normalised, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    # RFC 822, used by RSS.
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def classify_page(text: str) -> str:
    """Label a fetched page.

    Returns one of ``ok``, ``challenge``, ``ratelimited``, ``disabled``,
    ``protected``, ``missing``.
    """
    haystack = (text or "")[:20000].lower()
    if any(marker in haystack for marker in CHALLENGE_MARKERS):
        return "challenge"
    if any(marker in haystack for marker in RATE_LIMIT_MARKERS):
        return "ratelimited"
    if any(marker in haystack for marker in DISABLED_MARKERS):
        return "disabled"
    if any(marker in haystack for marker in PROTECTED_MARKERS):
        return "protected"
    if any(marker in haystack for marker in NOT_FOUND_MARKERS):
        return "missing"
    return "ok"


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = html_module.unescape(value)
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _inline_text(node) -> str:
    """Flatten a tweet body without injecting breaks around inline links."""
    if node is None:
        return ""
    for br in node.find_all("br"):
        br.replace_with("\n")
    return _clean_text(node.get_text())


def _stat_lookup(item) -> Dict[str, Optional[int]]:
    """Map Nitter's ``.tweet-stat`` icons onto engagement fields."""
    stats: Dict[str, Optional[int]] = {
        "replies": None,
        "retweets": None,
        "likes": None,
        "views": None,
    }
    icon_to_field = {
        "icon-comment": "replies",
        "icon-retweet": "retweets",
        "icon-heart": "likes",
        "icon-views": "views",
    }
    for stat in item.select(".tweet-stat"):
        icon = stat.select_one(".icon-container span")
        classes = " ".join(icon.get("class", [])) if icon else ""
        field = next((value for key, value in icon_to_field.items() if key in classes), None)
        if not field:
            continue
        stats[field] = count_to_int(stat.get_text(" ", strip=True))
    return stats


def parse_html_timeline(
    html: str, instance: str, include_replies: bool = True
) -> List[Dict[str, Any]]:
    """Extract tweets from a Nitter timeline or search result page."""
    soup = BeautifulSoup(html or "", "html.parser")
    tweets: List[Dict[str, Any]] = []

    for item in soup.select(".timeline-item"):
        if "show-more" in (item.get("class") or []):
            continue
        content = item.select_one(".tweet-content") or item.select_one(".tweet-body")
        if content is None:
            continue

        classes = item.get("class") or []
        is_reply = "tweet-body" in " ".join(classes) and item.select_one(
            ".replying-to"
        ) is not None
        if is_reply and not include_replies:
            continue

        text = _inline_text(content)
        if not text:
            continue

        date_link = item.select_one(".tweet-date a") or item.select_one("a.tweet-date")
        published = parse_timestamp(
            (date_link.get("title") if date_link else None)
            or (date_link.get_text(strip=True) if date_link else None)
        )

        link_el = item.select_one("a.tweet-link") or item.select_one(".tweet-date a")
        href = link_el.get("href") if link_el else None
        url = rewrite_host(href, instance) if href else None

        username_el = item.select_one(".username") or item.select_one(".tweet-header .username")
        username = username_el.get_text(strip=True).lstrip("@") if username_el else None
        fullname_el = item.select_one(".fullname")
        fullname = fullname_el.get_text(strip=True) if fullname_el else None

        stats = _stat_lookup(item)
        pinned = item.select_one(".pinned") is not None
        retweeted_by = item.select_one(".retweet-header .username")
        quoted = item.select_one(".quote .tweet-content")

        tweets.append(
            {
                "id": extract_status_id(url),
                "url": url,
                "text": text,
                "date": published,
                "author": username,
                "author_name": fullname,
                "likes": stats["likes"],
                "replies": stats["replies"],
                "retweets": stats["retweets"],
                "views": stats["views"],
                "is_retweet": retweeted_by is not None,
                "retweeted_by": retweeted_by.get_text(strip=True).lstrip("@")
                if retweeted_by
                else None,
                "quote": _inline_text(quoted) or None,
                "pinned": pinned,
                "media": [
                    rewrite_host(img.get("src"), instance)
                    for img in item.select(".attachments img, .still-image img")
                    if img.get("src")
                ],
            }
        )
    return tweets


def parse_html_cursor(html: str) -> Optional[str]:
    """Return the ``show-more`` cursor value from a results page, if any."""
    soup = BeautifulSoup(html or "", "html.parser")
    link = soup.select_one(".show-more a") or soup.select_one("a.more")
    if link is None:
        return None
    href = link.get("href") or ""
    if not href:
        return None
    query = parse_qs(urlparse(href).query)
    cursor = (query.get("cursor") or [None])[0]
    if cursor:
        return cursor
    # Older layouts put the raw cursor in the path segment.
    match = re.search(r"cursor=([^&]+)", href)
    return match.group(1) if match else None


def _strip_html(fragment: str) -> str:
    return _clean_text(BeautifulSoup(fragment or "", "html.parser").get_text("\n", strip=True))


def parse_rss_feed(xml: str, instance: str) -> List[Dict[str, Any]]:
    """Extract tweets from a Nitter RSS feed (``/<user>/rss`` or search feed).

    RSS is parsed with the standard library's ElementTree rather than an HTML
    parser: ``<link>`` is a void element in HTML, so an HTML parser silently
    drops its text and every tweet loses its URL.
    """
    if not xml or "<item" not in xml:
        return []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError:
        return []

    def text_of(node: ET.Element, *tags: str) -> Optional[str]:
        for tag in tags:
            found = node.findtext(tag)
            if found:
                return found.strip()
        return None

    dc_creator = "{http://purl.org/dc/elements/1.1/}creator"
    tweets: List[Dict[str, Any]] = []
    for item in root.iter("item"):
        description = text_of(item, "description") or ""
        headline = _clean_text(text_of(item, "title") or "")
        body = _strip_html(description)
        text = body or headline
        if not text:
            continue

        href = text_of(item, "link")
        guid = text_of(item, "guid")
        creator = text_of(item, dc_creator, "creator")
        tweets.append(
            {
                "id": guid or extract_status_id(href),
                "url": rewrite_host(href, instance) if href else None,
                "text": text,
                "date": parse_timestamp(text_of(item, "pubDate", "pubdate")),
                "author": creator.lstrip("@") if creator else None,
                "author_name": None,
                "likes": None,
                "replies": None,
                "retweets": None,
                "views": None,
                "is_retweet": False,
                "retweeted_by": None,
                "quote": None,
                "pinned": False,
                "media": [
                    rewrite_host(img.get("src"), instance)
                    for img in BeautifulSoup(description, "html.parser").find_all("img")
                    if img.get("src")
                ],
            }
        )
    return tweets


def detect_private(text: str, username: Optional[str] = None) -> bool:
    """True when a page is a protected-account notice rather than a timeline."""
    haystack = (text or "").lower()
    if any(marker in haystack for marker in PROTECTED_MARKERS):
        return True
    if username:
        needle = f"@{username.lower()}"
        if needle in haystack and "private" in haystack:
            return True
    return False


def iter_tweets(payload: str, instance: str) -> Iterator[Dict[str, Any]]:
    """Parse ``payload`` as RSS when it looks like XML, otherwise as HTML."""
    stripped = (payload or "").lstrip()
    if stripped.startswith("<?xml") or "<rss" in stripped[:200]:
        yield from parse_rss_feed(payload, instance)
    else:
        yield from parse_html_timeline(payload, instance)
