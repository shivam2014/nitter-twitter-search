"""Shared pytest fixtures.

Every test runs offline: network calls are monkeypatched and HTTP payloads come
from ``tests/fixtures``, captured from live instances.
"""

import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Keep instance/health caches out of the user's real cache directory."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path / "cache"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(scope="session")
def profile_html() -> str:
    return (FIXTURES / "profile.html").read_text()


@pytest.fixture(scope="session")
def search_html() -> str:
    return (FIXTURES / "search.html").read_text()


@pytest.fixture(scope="session")
def user_rss() -> str:
    return (FIXTURES / "user_rss.xml").read_text()


@pytest.fixture(scope="session")
def challenge_html() -> str:
    return (FIXTURES / "challenge.html").read_text()
