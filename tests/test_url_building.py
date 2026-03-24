"""Tests for URL building functionality in cli.py."""

import pytest
import sys
sys.path.insert(0, '../src')

from nitter_search.cli import build_search_url


class TestBuildSearchURL:
    """Test URL construction with various parameter combinations."""
    
    def test_basic_username_no_query(self):
        """Test basic username without query."""
        url = build_search_url(username="NASA", query=None, start_date=None, end_date=None, mirror="https://nitter.net")
        assert "nitter.net/NASA/search" in url
        assert "f=tweets" in url
        assert "q=" in url  # Empty query param present
    
    def test_username_with_query(self):
        """Test username with search query."""
        url = build_search_url(username="elonmusk", query="AI", start_date=None, end_date=None, mirror="https://nitter.net")
        assert "nitter.net/elonmusk/search" in url
        assert "q=AI" in url
    
    def test_username_with_date_range(self):
        """Test username with date range filters."""
        url = build_search_url(
            username="NASA", 
            query=None, 
            start_date="2026-03-23", 
            end_date="2026-03-24",
            mirror="https://nitter.net"
        )
        assert "since=2026-03-23" in url
        assert "until=2026-03-24" in url
    
    def test_username_with_query_and_dates(self):
        """Test all parameters combined."""
        url = build_search_url(
            username="NASA", 
            query="Mars", 
            start_date="2026-01-01", 
            end_date="2026-12-31",
            mirror="https://nitter.net"
        )
        assert "nitter.net/NASA/search" in url
        assert "q=Mars" in url
        assert "since=2026-01-01" in url
        assert "until=2026-12-31" in url
        assert "f=tweets" in url
    
    def test_no_username_query_only(self):
        """Test global search without username."""
        url = build_search_url(username=None, query="artificial intelligence", start_date=None, end_date=None, mirror="https://nitter.net")
        assert "nitter.net/search" in url  # No username in path
        assert "q=artificial+intelligence" in url  # URL encoded
    
    def test_special_characters_url_encoded(self):
        """Test that special characters are properly URL encoded."""
        url = build_search_url(username="NASA", query="test @mention #hashtag", start_date=None, end_date=None, mirror="https://nitter.net")
        assert "q=test" in url
        assert "+" in url  # Spaces become + or %20
    
    def test_different_mirror_urls(self):
        """Test with different Nitter mirror URLs."""
        mirrors = [
            "https://nitter.net",
            "https://nitter.moe",
            "https://nitter.pussthecat.org",
            "https://nitter.snopyta.org"
        ]
        
        for mirror in mirrors:
            url = build_search_url(username="test", query=None, start_date=None, end_date=None, mirror=mirror)
            assert mirror in url
    
    def test_empty_string_query(self):
        """Test empty string query handling."""
        url = build_search_url(username="NASA", query="", start_date=None, end_date=None, mirror="https://nitter.net")
        assert "q=" in url  # Empty but present
    
    def test_whitespace_only_query(self):
        """Test whitespace-only query is stripped."""
        url = build_search_url(username="NASA", query="   ", start_date=None, end_date=None, mirror="https://nitter.net")
        # Whitespace should be stripped to empty
        assert "q=" in url
    
    def test_only_start_date(self):
        """Test with only start date (no end date)."""
        url = build_search_url(username="NASA", query=None, start_date="2026-03-01", end_date=None, mirror="https://nitter.net")
        assert "since=2026-03-01" in url
        assert "until=" not in url
    
    def test_only_end_date(self):
        """Test with only end date (no start date)."""
        url = build_search_url(username="NASA", query=None, start_date=None, end_date="2026-03-31", mirror="https://nitter.net")
        assert "until=2026-03-31" in url
        assert "since=" not in url
    
    def test_url_structure(self):
        """Test overall URL structure is valid."""
        url = build_search_url(
            username="test_user", 
            query="test query", 
            start_date="2026-01-01", 
            end_date="2026-12-31",
            mirror="https://nitter.net"
        )
        
        # Should start with mirror URL
        assert url.startswith("https://nitter.net/")
        
        # Should have query parameters after ?
        assert "?" in url
        
        # Should have multiple parameters separated by &
        params = url.split("?")[1].split("&")
        assert len(params) >= 3  # At least f, q, and one date param


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
