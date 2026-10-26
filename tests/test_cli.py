"""CLI behaviour: output modes, exit codes and maintenance commands."""

import json
import sys

import pytest

import nitter_search  # noqa: F401
from nitter_search.cli import main

cli = sys.modules["nitter_search.cli"]

OK_PAYLOAD = {
    "search_metadata": {
        "user": "NASA",
        "query": None,
        "private_profile": False,
        "error": None,
        "total": 2,
        "method": "rss",
        "mirror_used": "https://a.example",
    },
    "tweets": [
        {"id": "1", "text": "first tweet", "date": "2026-10-25T00:00:00Z"},
        {"id": "2", "text": "second tweet", "date": "2026-10-24T00:00:00Z"},
    ],
}


@pytest.fixture
def patched_search(monkeypatch):
    def install(payload):
        monkeypatch.setattr(cli, "search", lambda request: payload)

    return install


class TestOutputModes:
    def test_json_is_default(self, patched_search, capsys):
        patched_search(OK_PAYLOAD)
        assert main(["--user", "NASA"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["search_metadata"]["total"] == 2

    def test_text_mode(self, patched_search, capsys):
        patched_search(OK_PAYLOAD)
        assert main(["--user", "NASA", "--text"]) == 0
        assert capsys.readouterr().out.strip().splitlines() == ["first tweet", "second tweet"]

    def test_ndjson_mode(self, patched_search, capsys):
        patched_search(OK_PAYLOAD)
        assert main(["--user", "NASA", "--ndjson"]) == 0
        lines = capsys.readouterr().out.strip().splitlines()
        assert [json.loads(line)["id"] for line in lines] == ["1", "2"]

    def test_pretty_mode_indents(self, patched_search, capsys):
        patched_search(OK_PAYLOAD)
        main(["--user", "NASA", "--pretty"])
        assert "\n  " in capsys.readouterr().out


class TestExitCodes:
    def test_success(self, patched_search):
        patched_search(OK_PAYLOAD)
        assert main(["--user", "NASA"]) == 0

    def test_no_results(self, patched_search):
        patched_search(
            {
                "search_metadata": {
                    "user": "NASA",
                    "private_profile": False,
                    "error": "No tweets found for that request.",
                    "total": 0,
                },
                "tweets": [],
            }
        )
        assert main(["--user", "NASA", "--quiet"]) == 3

    def test_private_profile(self, patched_search):
        patched_search(
            {
                "search_metadata": {
                    "user": "x",
                    "private_profile": True,
                    "error": "protected",
                    "total": 0,
                },
                "tweets": [],
            }
        )
        assert main(["--user", "x", "--quiet"]) == 2

    def test_hard_failure(self, patched_search):
        patched_search(
            {
                "search_metadata": {
                    "user": "x",
                    "private_profile": False,
                    "error": "Every instance failed.",
                    "total": 0,
                },
                "tweets": [],
            }
        )
        assert main(["--user", "x", "--quiet"]) == 1

    def test_missing_target_exits_2(self):
        with pytest.raises(SystemExit) as excinfo:
            main([])
        assert excinfo.value.code == 2


class TestRequestBuilding:
    def test_flags_map_to_request(self, monkeypatch):
        captured = {}

        def fake_search(request):
            captured["request"] = request
            return OK_PAYLOAD

        monkeypatch.setattr(cli, "search", fake_search)
        main(
            [
                "--user", "NASA",
                "--query", "mars",
                "--since", "2026-10-01",
                "--until", "2026-10-26",
                "--limit", "5",
                "--filter", "media",
                "--min-faves", "10",
                "--stats",
                "--no-browser",
                "--exclude-replies",
                "--instance", "https://a.example",
            ]
        )
        request = captured["request"]
        assert request.user == "NASA"
        assert request.query == "mars"
        assert request.since == "2026-10-01"
        assert request.limit == 5
        assert request.filters == ["media"]
        assert request.min_faves == 10
        assert request.with_stats is True
        assert request.allow_browser is False
        assert request.include_replies is False
        assert request.instances == ["https://a.example"]


class TestMaintenance:
    def test_check_reports_health(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.instances_mod, "check_all", lambda instances=None: [{"url": "https://a.example", "ok": True}])
        assert main(["--check"]) == 0
        assert json.loads(capsys.readouterr().out)[0]["ok"] is True

    def test_check_fails_when_all_down(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.instances_mod, "check_all", lambda instances=None: [{"url": "https://a.example", "ok": False}])
        assert main(["--check"]) == 1

    def test_list_instances(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.instances_mod, "discover", lambda force=False: [{"url": "https://a.example"}])
        assert main(["--list-instances"]) == 0
        assert json.loads(capsys.readouterr().out)[0]["url"] == "https://a.example"
