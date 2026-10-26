"""Command line interface for nitter-twitter-search."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from . import instances as instances_mod
from .search import SearchRequest, search
from .urls import SUPPORTED_FILTERS, ValidationError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOT_FOUND = 2
EXIT_NO_RESULTS = 3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nitter-search",
        description="Search Twitter/X through Nitter mirrors, with automatic instance fallback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nitter-search --user NASA --limit 10
  nitter-search --user elonmusk --query tesla --since 2026-10-01 --limit 30
  nitter-search --query "mars rover" --filter media --min-faves 100
  nitter-search --user NASA --stats --limit 5
  nitter-search --check
  nitter-search --list-instances
""",
    )
    target = parser.add_argument_group("what to search")
    target.add_argument("--query", "-q", help="Search text")
    target.add_argument("--user", "-u", help="Twitter username to scope the search to")
    target.add_argument("--since", "--start-date", dest="since", help="Earliest date (YYYY-MM-DD)")
    target.add_argument("--until", "--end-date", dest="until", help="Latest date (YYYY-MM-DD)")
    target.add_argument(
        "--filter",
        action="append",
        default=[],
        help=f"Nitter filter, repeatable: {', '.join(SUPPORTED_FILTERS)}",
    )
    target.add_argument("--min-faves", type=int, help="Minimum likes")
    target.add_argument("--min-retweets", type=int, help="Minimum retweets")
    target.add_argument("--min-replies", type=int, help="Minimum replies")

    output = parser.add_argument_group("output")
    output.add_argument("--limit", "--max-tweets", dest="limit", type=int, default=20,
                        help="Maximum tweets to return (default: 20)")
    output.add_argument("--json", action="store_true", help="Emit a single JSON document (default)")
    output.add_argument("--ndjson", action="store_true", help="Emit one JSON tweet per line")
    output.add_argument("--text", action="store_true", help="Emit tweet text only")
    output.add_argument("--pretty", action="store_true", help="Indent JSON output")

    runtime = parser.add_argument_group("runtime")
    runtime.add_argument("--instance", action="append", help="Pin a Nitter instance, repeatable")
    runtime.add_argument("--mirror", action="append", help="Alias for --instance")
    runtime.add_argument("--stats", action="store_true",
                         help="Use a browser to collect likes/replies/retweets")
    runtime.add_argument("--no-browser", action="store_true",
                         help="RSS only; fail instead of launching a browser")
    runtime.add_argument("--exclude-replies", action="store_true",
                         help="Drop replies from results")
    runtime.add_argument("--timeout", type=float, default=90.0,
                         help="Overall time budget in seconds (default: 90)")
    runtime.add_argument("--quiet", action="store_true", help="Suppress progress on stderr")

    maintenance = parser.add_argument_group("maintenance")
    maintenance.add_argument("--check", action="store_true", help="Probe instances and report health")
    maintenance.add_argument("--list-instances", action="store_true", help="List instances to try")
    maintenance.add_argument("--refresh", action="store_true", help="Ignore the cached instance list")
    return parser


def _emit(payload: Dict[str, Any], args: argparse.Namespace) -> None:
    tweets: List[Dict[str, Any]] = payload.get("tweets", [])
    if args.text:
        for tweet in tweets:
            print(tweet.get("text", "").replace("\n", " "))
        return
    if args.ndjson:
        for tweet in tweets:
            print(json.dumps(tweet, ensure_ascii=False, default=str))
        return
    indent = 2 if args.pretty else None
    print(json.dumps(payload, indent=indent, ensure_ascii=False, default=str))


def _exit_code(payload: Dict[str, Any]) -> int:
    metadata = payload.get("search_metadata", {})
    if metadata.get("private_profile"):
        return EXIT_NOT_FOUND
    if metadata.get("error"):
        if not payload.get("tweets"):
            message = str(metadata["error"]).lower()
            if "no tweets found" in message:
                return EXIT_NO_RESULTS
            return EXIT_ERROR
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.check:
        results = instances_mod.check_all(instances=args.instance or args.mirror)
        print(json.dumps(results, indent=2 if args.pretty else None))
        return EXIT_OK if any(item["ok"] for item in results) else EXIT_ERROR

    if args.list_instances:
        records = instances_mod.discover(force=args.refresh)
        print(json.dumps(records, indent=2 if args.pretty else None))
        return EXIT_OK

    if not args.query and not args.user:
        parser.error("provide --user, --query, or one of --check / --list-instances")

    request = SearchRequest(
        user=args.user,
        query=args.query,
        since=args.since,
        until=args.until,
        limit=args.limit,
        filters=args.filter,
        min_faves=args.min_faves,
        min_retweets=args.min_retweets,
        min_replies=args.min_replies,
        instances=(args.instance or args.mirror),
        with_stats=args.stats,
        allow_browser=not args.no_browser,
        include_replies=not args.exclude_replies,
        timeout=args.timeout,
    )

    try:
        payload = search(request)
    except ValidationError as exc:
        if not args.quiet:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        return 130

    _emit(payload, args)
    code = _exit_code(payload)
    if code != EXIT_OK and not args.quiet:
        metadata = payload.get("search_metadata", {})
        detail = metadata.get("error") or ", ".join(
            f"{item['url']}: {item.get('error')}" for item in metadata.get("instances_tried", [])
        )
        print(detail, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
