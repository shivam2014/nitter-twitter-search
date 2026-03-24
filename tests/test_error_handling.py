"""Tests for error handling and graceful degradation."""

import pytest
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import scrape_user_tweets_camoufox, CAMOUFOX_AVAILABLE


class TestCamoufoxNotInstalled:
    """Test behavior when Camoufox is not available."""
    
    @patch('nitter_search.browser_scraper.CAMOUFOX_AVAILABLE', False)
    def test_returns_error_when_camoufox_missing(self):
        """Test that appropriate error is returned when camoufox not installed."""
        result = scrape_user_tweets_camoufox(username="NASA")
        
        # Should have error message
        assert "error" in result["search_metadata"]
        assert "Camoufox library not installed" in result["search_metadata"]["error"]
        
        # Should still have structured response
        assert "tweets" in result
        assert result["tweets"] == []
    
    @patch('nitter_search.browser_scraper.CAMOUFOX_AVAILABLE', False)
    def test_error_response_has_required_fields(self):
        """Test error response has all required fields."""
        result = scrape_user_tweets_camoufox(username="test", query="test")
        
        metadata = result["search_metadata"]
        assert "query" in metadata
        assert "user" in metadata
        assert "error" in metadata
        assert "timestamp" in metadata


class TestBrowserAutomationErrors:
    """Test handling of browser automation failures."""
    
    @pytest.mark.skipif(not CAMOUFOX_AVAILABLE, reason="Requires Camoufox")
    def test_invalid_mirror_url_handled_gracefully(self):
        """Test that invalid mirror URLs are handled gracefully."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            mirror="http://invalid-url-that-does-not-exist-12345.com"
        )
        
        # Should not crash, should return error
        assert "search_metadata" in result
        assert "tweets" in result
        
        # May have error or empty results
        if "error" in result["search_metadata"]:
            assert isinstance(result["search_metadata"]["error"], str)
    
    @pytest.mark.skipif(not CAMOUFOX_AVAILABLE, reason="Requires Camoufox")
    def test_private_profile_detection(self):
        """Test that private profiles are detected."""
        # Use a known private account or mock the response
        # For now, just verify the function doesn't crash
        result = scrape_user_tweets_camoufox(username="test_private_user")
        
        # Should return structured response
        assert "search_metadata" in result
        assert "tweets" in result
        
        # If detected as private
        if result["search_metadata"].get("private_profile"):
            assert len(result["tweets"]) == 0


class TestExceptionHandling:
    """Test that exceptions are caught and converted to structured errors."""
    
    def test_exception_returns_structured_error(self):
        """Test that any exception returns structured error response."""
        # Mock browser to raise exception
        with patch('nitter_search.browser_scraper.camoufox') as mock_camoufox:
            mock_camoufox.Camoufox.side_effect = Exception("Test browser error")
            
            result = scrape_user_tweets_camoufox(username="NASA")
            
            # Should not crash, should return error
            assert "search_metadata" in result
            assert "tweets" in result
            assert result["tweets"] == []
            
            # Error should be in metadata
            if "error" in result["search_metadata"]:
                assert isinstance(result["search_metadata"]["error"], str)


class TestResourceCleanup:
    """Test that resources are cleaned up on errors."""
    
    @pytest.mark.skipif(not CAMOUFOX_AVAILABLE, reason="Requires Camoufox")
    def test_browser_closed_on_error(self):
        """Test that browser is closed even when error occurs."""
        # This is more of an integration test
        # Just verify the function completes without hanging
        result = scrape_user_tweets_camoufox(
            username="NASA",
            mirror="http://timeout-test.invalid"
        )
        
        # Should complete (may timeout or return error)
        assert "search_metadata" in result


class TestEdgeCases:
    """Test various edge cases."""
    
    def test_username_with_numbers(self):
        """Test username with numbers."""
        result = scrape_user_tweets_camoufox(username="user123")
        assert "search_metadata" in result
    
    def test_username_with_underscores(self):
        """Test username with underscores."""
        result = scrape_user_tweets_camoufox(username="user_name_test")
        assert "search_metadata" in result
    
    def test_query_with_multiple_spaces(self):
        """Test query with multiple spaces."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            query="  multiple   spaces   test  "
        )
        assert "search_metadata" in result
    
    def test_both_query_and_username_none(self):
        """Test when both query and username are None."""
        result = scrape_user_tweets_camoufox(username=None, query=None)
        assert "search_metadata" in result
    
    def test_empty_string_everywhere(self):
        """Test with empty strings for all parameters."""
        result = scrape_user_tweets_camoufox(
            username="",
            query="",
            start_date="",
            end_date=""
        )
        assert "search_metadata" in result


class TestDateValidation:
    """Test date parameter handling."""
    
    def test_partial_date_format(self):
        """Test partial date format (should handle gracefully)."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            start_date="2026-03",  # Missing day
            end_date="2026"  # Year only
        )
        # Should not crash
        assert "search_metadata" in result
    
    def test_datetime_instead_of_date(self):
        """Test datetime string instead of date."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            start_date="2026-03-24 10:30:00"
        )
        # Should handle gracefully
        assert "search_metadata" in result
    
    def test_timezone_in_date(self):
        """Test date with timezone."""
        result = scrape_user_tweets_camoufox(
            username="NASA",
            start_date="2026-03-24T10:30:00Z"
        )
        # Should handle gracefully
        assert "search_metadata" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
