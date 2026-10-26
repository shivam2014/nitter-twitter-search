"""MCP server exposing Nitter search as tools over stdio.

Designed to be registered once and left running: the browser session and the
instance list are reused across tool calls, so only the first search pays the
startup cost.

Wire it up with:

    opencode mcp add nitter -- global \
      nitter-search-mcp

or in ``opencode.json``::

    {"mcp": {"servers": {"nitter": {
        "type": "local",
        "command": ["nitter-search-mcp"]
    }}}}
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from . import instances as instances_mod
from .search import SearchRequest, search
from .transport import get_default_session, shutdown_default_session
from .urls import ValidationError

SERVER_NAME = "nitter-twitter-search"
SERVER_VERSION = "2.0.0"
DEFAULT_PROTOCOL = "2025-06-18"
IDLE_SHUTDOWN = 600.0

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "search_tweets",
        "description": (
            "Search public Twitter/X posts through Nitter mirrors. Scopes to a user "
            "when 'user' is given, otherwise searches globally. Returns tweets with "
            "text, date, URL and (when with_stats is true) engagement counts. "
            "Automatically falls back across healthy instances."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text, e.g. 'mars rover'"},
                "user": {
                    "type": "string",
                    "description": "Twitter username without @, e.g. 'NASA'",
                },
                "since": {"type": "string", "description": "Earliest date, YYYY-MM-DD"},
                "until": {"type": "string", "description": "Latest date, YYYY-MM-DD"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum tweets to return (default 20)",
                },
                "filters": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Nitter filters: media, links, quotes, replies",
                },
                "min_faves": {"type": "integer", "description": "Minimum likes"},
                "min_retweets": {"type": "integer", "description": "Minimum retweets"},
                "min_replies": {"type": "integer", "description": "Minimum replies"},
                "with_stats": {
                    "type": "boolean",
                    "description": (
                        "Use a browser to collect like/reply/retweet counts. Slower "
                        "(several seconds) but returns engagement data."
                    ),
                },
                "instance": {
                    "type": "string",
                    "description": "Pin one Nitter instance URL instead of auto-selecting",
                },
            },
            "anyOf": [{"required": ["query"]}, {"required": ["user"]}],
        },
    },
    {
        "name": "user_tweets",
        "description": (
            "Get a user's recent tweets, newest first. Faster than search_tweets "
            "because it uses the timeline feed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "user": {"type": "string", "description": "Twitter username without @"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
                "with_stats": {"type": "boolean", "description": "Collect engagement counts"},
                "instance": {"type": "string", "description": "Pin one instance URL"},
            },
            "required": ["user"],
        },
    },
    {
        "name": "list_nitter_instances",
        "description": (
            "List Nitter instances this server would try, healthiest first. Set "
            "probe=true to test each one live by fetching a feed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "probe": {"type": "boolean", "description": "Actively test each instance"},
                "refresh": {"type": "boolean", "description": "Ignore the cached list"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
        },
    },
]

_last_call = time.monotonic()


def _log(message: str) -> None:
    print(f"[nitter-mcp] {message}", file=sys.stderr, flush=True)


def _trim(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep tool results small enough to stay useful in a context window."""
    metadata = dict(payload.get("search_metadata") or {})
    tried = metadata.get("instances_tried") or []
    metadata["instances_tried"] = [
        {"url": item.get("url"), "ok": item.get("ok"), "method": item.get("method")}
        for item in tried
    ]
    return {
        "search_metadata": metadata,
        "tweets": payload.get("tweets", []),
    }


def _run_search(arguments: Dict[str, Any], *, force_user_only: bool = False) -> Dict[str, Any]:
    user = arguments.get("user")
    if force_user_only and not user:
        raise ValidationError("'user' is required")
    if not user and not arguments.get("query"):
        raise ValidationError("Pass 'query', 'user', or both")
    request = SearchRequest(
        user=user,
        query=None if force_user_only else arguments.get("query"),
        since=arguments.get("since"),
        until=arguments.get("until"),
        limit=int(arguments.get("limit") or 20),
        filters=[str(value) for value in (arguments.get("filters") or [])],
        min_faves=arguments.get("min_faves"),
        min_retweets=arguments.get("min_retweets"),
        min_replies=arguments.get("min_replies"),
        instances=[arguments["instance"]] if arguments.get("instance") else None,
        with_stats=bool(arguments.get("with_stats")),
    )
    return _trim(search(request))


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch one ``tools/call`` request."""
    if name == "search_tweets":
        return _run_search(arguments)
    if name == "user_tweets":
        return _run_search(arguments, force_user_only=True)
    if name == "list_nitter_instances":
        if arguments.get("probe"):
            results = instances_mod.check_all(
                instances=None, limit=int(arguments.get("limit") or 5)
            )
            return {"instances": results}
        records = instances_mod.discover(force=bool(arguments.get("refresh")))
        return {"instances": records[: int(arguments.get("limit") or 10)]}
    raise ValidationError(f"Unknown tool: {name}")


def _result(payload: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, default=str, indent=None)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": is_error,
    }


def handle(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC message, returning a response or ``None``."""
    method = message.get("method")
    request_id = message.get("id")

    if request_id is None:
        # Notification: nothing to answer.
        return None

    def ok(result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def error(code: int, text: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": text}}

    if method == "initialize":
        params = message.get("params") or {}
        requested = params.get("protocolVersion")
        protocol = requested if isinstance(requested, str) else DEFAULT_PROTOCOL
        return ok(
            {
                "protocolVersion": protocol,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Search public X/Twitter posts via Nitter. Prefer user_tweets for "
                    "a person's timeline; use search_tweets for keyword or date-scoped "
                    "searches. Set with_stats=true only when engagement counts matter."
                ),
            }
        )
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return error(-32602, "tools/call requires a tool name")
        if not isinstance(arguments, dict):
            return error(-32602, "arguments must be an object")
        try:
            payload = call_tool(name, arguments)
        except ValidationError as exc:
            return ok(_result({"error": str(exc)}, is_error=True))
        except Exception as exc:  # keep the server alive on tool failure
            _log(f"tool {name} failed: {exc}")
            return ok(_result({"error": f"{type(exc).__name__}: {exc}"}, is_error=True))
        return ok(_result(payload))
    if method in {"resources/list", "prompts/list"}:
        key = "resources" if method.startswith("resources") else "prompts"
        return ok({key: []})
    return error(-32601, f"Method not found: {method}")


def serve(stdin=None, stdout=None) -> None:
    """Read newline-delimited JSON-RPC from ``stdin`` until it closes."""
    source = stdin or sys.stdin
    sink = stdout or sys.stdout
    _log(f"{SERVER_NAME} {SERVER_VERSION} ready")
    global _last_call
    try:
        for line in source:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                sink.write(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32700, "message": "Parse error"},
                        }
                    )
                    + "\n"
                )
                sink.flush()
                continue
            response = handle(message) if isinstance(message, dict) else None
            _last_call = time.monotonic()
            if response is not None:
                sink.write(json.dumps(response, ensure_ascii=False, default=str) + "\n")
                sink.flush()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            shutdown_default_session()
        except Exception:
            pass
        _log("shutting down")


def main() -> int:
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
