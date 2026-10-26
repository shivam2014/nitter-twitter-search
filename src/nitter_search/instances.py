"""Nitter instance discovery, health probing and ranking.

Public Nitter instances come and go, and the set that works changes monthly.
Rather than hard-coding a list that rots, we ask a status aggregator which
instances are healthy right now, keep its answer in a small cache, and fall back
to a seed list when the aggregator is unreachable.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .parse import classify_page
from .urls import normalize_instance

STATUS_URL = "https://status.d420.de/api/v1/instances"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
DISCOVERY_TTL = 6 * 60 * 60

#: Known-good instances, used only when discovery is unavailable.
SEED_INSTANCES = (
    "https://nitter.netbub.com",
    "https://nitter.mizuki.st",
    "https://nitter.tiekoetter.com",
    "https://nitter.pp.ua",
)

#: Instances that are known to be dead or permanently closed.
KNOWN_DEAD = {
    "nitter.net",
    "nitter.moe",
    "nitter.pussthecat.org",
    "nitter.snopyta.org",
    "xcancel.com",
    "nitter.poast.org",
    "nitter.woodland.cafe",
    "nitter.kavin.rocks",
}


def cache_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    path = Path(root) / "nitter-search"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_file() -> Path:
    return cache_dir() / "instances.json"


def health_file() -> Path:
    return cache_dir() / "health.json"


#: How long a failure keeps an instance out of the preferred order.
HEALTH_TTL = 15 * 60


def _read_health() -> Dict[str, Dict[str, float]]:
    path = health_file()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_health(state: Dict[str, Dict[str, float]]) -> None:
    try:
        health_file().write_text(json.dumps(state, indent=2))
    except OSError:
        pass


def record_result(instance: str, ok: bool) -> None:
    """Remember whether an instance answered, so later calls skip dead ones."""
    try:
        key = normalize_instance(instance)
    except ValueError:
        return
    state = _read_health()
    entry = dict(state.get(key) or {})
    now = time.time()
    if ok:
        entry.update(last_ok=now, failures=0)
    else:
        entry.update(last_fail=now, failures=float(entry.get("failures", 0)) + 1)
    state[key] = entry
    # Prune entries that no longer matter.
    for url in list(state):
        entry = state.get(url) or {}
        newest = max(float(entry.get("last_ok", 0)), float(entry.get("last_fail", 0)))
        if now - newest > HEALTH_TTL * 8:
            state.pop(url, None)
    _write_health(state)


def _health_rank(instance: str, state: Dict[str, Dict[str, float]]) -> int:
    """0 = recently worked, 1 = unknown, 2 = failed recently."""
    entry = state.get(instance)
    if not entry:
        return 1
    now = time.time()
    failed = now - float(entry.get("last_fail", 0)) < HEALTH_TTL
    worked = now - float(entry.get("last_ok", 0)) < HEALTH_TTL * 4
    if failed:
        return 2
    if worked:
        return 0
    return 1


def _http_get(url: str, timeout: float = 8.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _read_cache() -> List[Dict[str, Any]]:
    path = cache_file()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    if time.time() - float(payload.get("fetched_at", 0)) > DISCOVERY_TTL:
        return []
    hosts = payload.get("hosts")
    return hosts if isinstance(hosts, list) else []


def _write_cache(hosts: List[Dict[str, Any]]) -> None:
    try:
        cache_file().write_text(
            json.dumps({"fetched_at": time.time(), "hosts": hosts}, indent=2)
        )
    except OSError:
        pass


def _hostname(instance: str) -> str:
    return normalize_instance(instance).split("://", 1)[1].split(":", 1)[0]


def fetch_status(timeout: float = 8.0) -> List[Dict[str, Any]]:
    """Return the aggregator's instance list, or ``[]`` when it is unreachable."""
    try:
        payload = json.loads(_http_get(STATUS_URL, timeout=timeout))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return []
    hosts = payload.get("hosts") if isinstance(payload, dict) else None
    return hosts if isinstance(hosts, list) else []


def discover(
    force: bool = False, timeout: float = 8.0, include_unknown: bool = False
) -> List[Dict[str, Any]]:
    """Return instance records, healthiest first.

    Each record is ``{"url", "healthy", "rss", "points", "bad"}``. Unhealthy
    instances are dropped unless ``include_unknown`` is set.
    """
    hosts = [] if force else _read_cache()
    if not hosts:
        hosts = fetch_status(timeout=timeout)
        if hosts:
            _write_cache(hosts)

    records: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for host in hosts:
        if not isinstance(host, dict):
            continue
        url = host.get("url")
        if not url:
            continue
        try:
            normalized = normalize_instance(url)
        except ValueError:
            continue
        if _hostname(normalized) in KNOWN_DEAD or normalized in seen:
            continue
        seen.add(normalized)
        healthy = bool(host.get("healthy"))
        bad = bool(host.get("is_bad_host"))
        if bad:
            continue
        if not healthy and not include_unknown:
            continue
        records.append(
            {
                "url": normalized,
                "healthy": healthy,
                "rss": bool(host.get("rss")),
                "bad": bad,
                "points": int(host.get("points") or 0),
                "version": host.get("version") or "",
            }
        )

    records.sort(key=lambda record: (record["bad"], not record["healthy"], -record["points"]))

    for seed in SEED_INSTANCES:
        normalized = normalize_instance(seed)
        if normalized in seen or _hostname(normalized) in KNOWN_DEAD:
            continue
        seen.add(normalized)
        records.append(
            {
                "url": normalized,
                "healthy": None,
                "rss": None,
                "bad": False,
                "points": 0,
                "version": "",
            }
        )

    health = _read_health()
    for record in records:
        record["health"] = _health_rank(record["url"], health)
    records.sort(
        key=lambda record: (
            record["bad"],
            not record["healthy"],
            record["health"],
            -record["points"],
        )
    )
    return records


def candidates(
    override: Optional[Iterable[str]] = None,
    limit: int = 5,
    force: bool = False,
    timeout: float = 8.0,
) -> List[str]:
    """Return instance URLs to try, in order."""
    if override:
        ordered: List[str] = []
        for value in override:
            normalized = normalize_instance(value)
            if normalized not in ordered:
                ordered.append(normalized)
        return ordered
    return [record["url"] for record in discover(force=force, timeout=timeout)][:limit]


def probe(instance: str, timeout: float = 8.0) -> Dict[str, Any]:
    """Check one instance by requesting a known account's RSS feed."""
    base = normalize_instance(instance)
    started = time.monotonic()
    result: Dict[str, Any] = {
        "url": base,
        "ok": False,
        "challenge": False,
        "rss": False,
        "latency_ms": None,
        "detail": "",
    }
    try:
        body = _http_get(f"{base}/NASA/rss", timeout=timeout)
    except urllib.error.HTTPError as exc:
        result["detail"] = f"HTTP {exc.code}"
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        return result
    except (urllib.error.URLError, OSError) as exc:
        result["detail"] = str(getattr(exc, "reason", exc))[:160]
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        return result

    result["latency_ms"] = int((time.monotonic() - started) * 1000)
    state = classify_page(body)
    has_items = "<item>" in body
    result["challenge"] = state == "challenge"
    result["rss"] = has_items
    result["ok"] = has_items
    result["detail"] = state if state != "ok" else ""
    return result


def check_all(instances: Optional[Iterable[str]] = None, limit: int = 8) -> List[Dict[str, Any]]:
    """Probe several instances and return their status, healthy first."""
    targets = list(instances) if instances else candidates(limit=limit)
    results = [probe(target) for target in targets]
    results.sort(key=lambda item: (not item["ok"], item["latency_ms"] or 10**6))
    return results
