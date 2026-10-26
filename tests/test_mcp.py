"""MCP server: JSON-RPC handshake, tool catalog, dispatch and errors."""

import io
import json
import sys

import pytest

import nitter_search  # noqa: F401
from nitter_search.mcp_server import TOOLS, handle, serve

mcp = sys.modules["nitter_search.mcp_server"]


def rpc(method, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


class TestHandshake:
    def test_initialize_echoes_protocol(self):
        response = handle(
            rpc(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            )
        )
        assert response["result"]["protocolVersion"] == "2025-06-18"
        assert response["result"]["serverInfo"]["name"] == "nitter-twitter-search"
        assert "tools" in response["result"]["capabilities"]

    def test_initialize_without_version_uses_default(self):
        response = handle(rpc("initialize", {}))
        assert response["result"]["protocolVersion"]

    def test_notifications_get_no_response(self):
        assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    def test_ping(self):
        assert handle(rpc("ping"))["result"] == {}


class TestToolCatalog:
    def test_lists_all_tools(self):
        tools = handle(rpc("tools/list"))["result"]["tools"]
        names = [tool["name"] for tool in tools]
        assert names == ["search_tweets", "user_tweets", "list_nitter_instances"]

    def test_schemas_are_objects(self):
        for tool in TOOLS:
            assert tool["inputSchema"]["type"] == "object"
            assert tool["description"]

    def test_search_requires_a_target(self):
        schema = TOOLS[0]["inputSchema"]
        assert "anyOf" in schema

    def test_user_tweets_requires_user(self):
        assert TOOLS[1]["inputSchema"]["required"] == ["user"]


class TestToolCalls:
    def test_dispatches_and_returns_json_content(self, monkeypatch):
        monkeypatch.setattr(
            mcp, "call_tool", lambda name, args: {"received": name, "args": args}
        )
        response = handle(
            rpc("tools/call", {"name": "user_tweets", "arguments": {"user": "NASA"}})
        )
        result = response["result"]
        assert result["isError"] is False
        assert json.loads(result["content"][0]["text"])["received"] == "user_tweets"
        assert result["structuredContent"]["args"] == {"user": "NASA"}

    def test_validation_error_is_reported_not_raised(self):
        response = handle(
            rpc("tools/call", {"name": "search_tweets", "arguments": {}})
        )
        assert response["result"]["isError"] is True
        message = json.loads(response["result"]["content"][0]["text"])["error"].lower()
        assert "query" in message and "user" in message

    def test_unknown_tool(self):
        response = handle(rpc("tools/call", {"name": "nope", "arguments": {}}))
        assert response["result"]["isError"] is True

    def test_crash_is_contained(self, monkeypatch):
        def boom(name, args):
            raise RuntimeError("kaboom")

        monkeypatch.setattr(mcp, "call_tool", boom)
        response = handle(rpc("tools/call", {"name": "user_tweets", "arguments": {}}))
        assert response["result"]["isError"] is True
        assert "kaboom" in response["result"]["content"][0]["text"]

    def test_missing_tool_name(self):
        response = handle(rpc("tools/call", {"arguments": {}}))
        assert response["error"]["code"] == -32602


class TestProtocolErrors:
    def test_unknown_method(self):
        assert handle(rpc("does/not/exist"))["error"]["code"] == -32601

    def test_parse_error_gets_id_null(self, monkeypatch):
        monkeypatch.setattr(mcp, "serve", serve)
        stdin = io.StringIO("{not json}\n")
        stdout = io.StringIO()
        serve(stdin=stdin, stdout=stdout)
        payload = json.loads(stdout.getvalue().splitlines()[0])
        assert payload["error"]["code"] == -32700

    def test_full_round_trip(self):
        requests = "\n".join(
            json.dumps(message)
            for message in [
                rpc("initialize", {"protocolVersion": "2025-06-18"}, 1),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                rpc("tools/list", None, 2),
            ]
        )
        stdout = io.StringIO()
        serve(stdin=io.StringIO(requests + "\n"), stdout=stdout)
        lines = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
        assert len(lines) == 2
        assert lines[0]["id"] == 1
        assert lines[1]["result"]["tools"]
