"""Tests for input validation in browser_scraper.py."""

import pytest
import sys
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import scrape_user_tweets_camoufox


class TestInputValidation:
    """Test input validation and edge cases."""
    
    def test_empty_username_returns_error(self):
        """Test that empty username returns appropriate error."""
        result = scrape_user_tweets_camoufox(username="")
        
        # Should return structured response even with invalid input
        assert "search_metadata" in result
        assert "tweets" in result
        assert isinstance(result["tweets"], list)
    
    def test_none_username(self):
        """Test None username handling."""
        result = scrape_user_tweets_camoufox(username=None)
        
        # Should handle gracefully
        assert "search_metadata" in result
        assert "tweets" in result
    
    def test_very_long_username(self):
        """Test with unusually long username."""
        long_username = "a" * 500
        result = scrape_user_tweets_camoufox(username=long_username)
        
        # Should not crash, just return empty or error
        assert "search_metadata" in result
        assert result["search_metadata"]["user"] == long_username
    
    def test_negative_max_tweets(self):
        """Test negative max_tweets value."""
        result = scrape_user_tweets_camoufox(username="NASA", max_tweets=-10)
        
        # Should handle gracefully (may return 0 tweets)
        assert "tweets" in result
        assert isinstance(result["tweets"], list)
    
    def test_zero_max_tweets(self):
        """Test zero max_tweets value."""
        result = scrape_user_tweets_camoufox(username="NASA", max_tweets=0)
        
        # Should return empty list
        assert len(result["tweets"]) == 0
    
    def test_very_large_max_tweets(self):
        """Test very large max_tweets value."""
        result = scrape_user_tweets_camoufox(username="NASA", max_tweets=1000000)
        
        # Should not crash, just may take longer
        assert "tweets" in result
        assert isinstance(result["tweets"], list)
    
    def test_invalid_date_format(self):
        """Test invalid date format handling."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            start_date="invalid-date",
            end_date="also-invalid"
        )
        
        # Should not crash, may return error or ignore dates
        assert "search_metadata" in result
    
    def test_future_dates(self):
        """Test with future dates (should still work)."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            start_date="2030-01-01",
            end_date="2030-12-31"
        )
        
        # Should not crash, just return empty results
        assert "search_metadata" in result
        assert "tweets" in result
    
    def test_start_after_end_date(self):
        """Test when start date is after end date."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            start_date="2026-12-31",
            end_date="2026-01-01"
        )
        
        # Should not crash, may return empty or error
        assert "search_metadata" in result
    
    def test_special_characters_in_username(self):
        """Test username with special characters."""
        result = scrape_user_tweets_camoufox(username="NASA_123!")
        
        # Should handle gracefully
        assert "search_metadata" in result
    
    def test_unicode_in_query(self):
        """Test query with unicode characters."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            query="火星 🚀 探索"  # Mars emoji and Chinese
        )
        
        # Should not crash
        assert "search_metadata" in result
    
    def test_sql_injection_attempt(self):
        """Test that SQL injection attempts are handled safely."""
        malicious_query = "' OR '1'='1"
        result = scrape_user_tweets_camoufox(username="NASA", query=malicious_query)
        
        # Should not crash or execute injection
        assert "search_metadata" in result
        assert result["search_metadata"]["query"] == malicious_query
    
    def test_xss_attempt_in_query(self):
        """Test XSS attempt in query parameter."""
        xss_query = "<script>alert('xss')</script>"
        result = scrape_user_tweets_camoufox(username="NASA", query=xss_query)
        
        # Should handle safely (URL encoding should prevent issues)
        assert "search_metadata" in result
    
    def test_malformed_mirror_url(self):
        """Test with malformed mirror URL."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            mirror="not-a-valid-url"
        )
        
        # Should return error, not crash
        assert "search_metadata" in result
        # May have error or just return empty
    
    def test_mirror_without_https(self):
        """Test mirror URL without https:// prefix."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            mirror="nitter.net"
        )
        
        # Should handle gracefully (may fail to connect)
        assert "search_metadata" in result
    
    def test_empty_query_string(self):
        """Test empty query string."""
        result = scrape_user_tweets_camoufox(username="NASA", query="")
        
        # Empty query should be treated as no filter
        assert "search_metadata" in result
    
    def test_whitespace_only_query(self):
        """Test whitespace-only query."""
        result = scrape_user_tweets_camoufox(username="NASA", query="   \t\n  ")
        
        # Should handle gracefully
        assert "search_metadata" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
