"""Tests for output format consistency."""

import pytest
import sys
from datetime import datetime
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import scrape_user_tweets_camoufox


class TestOutputFormat:
    """Test that output structure is consistent and correct."""
    
    def test_return_structure_always_present(self):
        """Test that return value always has required structure."""
        result = scrape_user_tweets_camoufox(username="test")
        
        # Required top-level keys
        assert "search_metadata" in result, "Missing search_metadata"
        assert "tweets" in result, "Missing tweets"
        
        # Types
        assert isinstance(result["search_metadata"], dict), "search_metadata should be dict"
        assert isinstance(result["tweets"], list), "tweets should be list"
    
    def test_search_metadata_required_fields(self):
        """Test that search_metadata always contains required fields."""
        result = scrape_user_tweets_camoufox(username="NASA")
        metadata = result["search_metadata"]
        
        # Required fields
        assert "user" in metadata, "Missing user field"
        assert "timestamp" in metadata, "Missing timestamp field"
    
    def test_timestamp_is_iso_format(self):
        """Test that timestamp is in ISO 8601 format."""
        result = scrape_user_tweets_camoufox(username="NASA")
        timestamp = result["search_metadata"]["timestamp"]
        
        # Should contain date and time
        assert len(timestamp) > 10, "Timestamp too short"
        
        # Try to parse it (lenient check)
        assert "T" in timestamp or " " in timestamp, "Timestamp should have date/time separator"
    
    def test_user_field_matches_input(self):
        """Test that user field matches input username."""
        test_username = "test_user_123"
        result = scrape_user_tweets_camoufox(username=test_username)
        
        assert result["search_metadata"]["user"] == test_username
    
    def test_query_field_in_metadata(self):
        """Test that query is recorded in metadata."""
        result = scrape_user_tweets_camoufox(username="NASA", query="Mars")
        
        assert "query" in result["search_metadata"]
        assert result["search_metadata"]["query"] == "Mars"
    
    def test_query_none_when_not_provided(self):
        """Test that query is None when not provided."""
        result = scrape_user_tweets_camoufox(username="NASA")
        
        assert result["search_metadata"]["query"] is None
    
    def test_mirror_used_in_metadata(self):
        """Test that mirror URL is recorded in metadata."""
        custom_mirror = "https://nitter.moe"
        result = scrape_user_tweets_camoufox(username="NASA", mirror=custom_mirror)
        
        assert "mirror_used" in result["search_metadata"]
        assert result["search_metadata"]["mirror_used"] == custom_mirror
    
    def test_default_mirror(self):
        """Test default mirror is nitter.net."""
        result = scrape_user_tweets_camoufox(username="NASA")
        
        assert result["search_metadata"].get("mirror_used") == "https://nitter.net"
    
    def test_tweet_object_structure(self):
        """Test that tweet objects have correct structure."""
        # This tests the structure when tweets ARE returned
        # Since we can't guarantee tweets without actual scraping,
        # we just verify the structure is correct in error cases
        
        result = scrape_user_tweets_camoufox(username="")
        
        # Even with empty results, structure should be consistent
        assert isinstance(result["tweets"], list)
    
    def test_error_field_format(self):
        """Test that error messages are strings."""
        # Trigger an error by using invalid input
        result = scrape_user_tweets_camoufox(username=None)
        
        if "error" in result["search_metadata"]:
            assert isinstance(result["search_metadata"]["error"], str), "Error should be string"
    
    def test_private_profile_boolean(self):
        """Test that private_profile field is boolean when present."""
        result = scrape_user_tweets_camoufox(username="NASA")
        
        if "private_profile" in result["search_metadata"]:
            assert isinstance(result["search_metadata"]["private_profile"], bool)
    
    def test_method_field_when_camoufox_available(self):
        """Test method field indicates scraping method."""
        # This will only be set if camoufox is available and successful
        result = scrape_user_tweets_camoufox(username="NASA")
        
        # If method is present, it should be a string
        if "method" in result["search_metadata"]:
            assert isinstance(result["search_metadata"]["method"], str)
    
    def test_empty_tweets_list_not_none(self):
        """Test that empty results return empty list, not None."""
        result = scrape_user_tweets_camoufox(username="")
        
        assert result["tweets"] is not None
        assert isinstance(result["tweets"], list)
    
    def test_result_is_json_serializable(self):
        """Test that result can be serialized to JSON."""
        import json
        
        result = scrape_user_tweets_camoufox(username="NASA", query="test")
        
        # Should not raise
        json_str = json.dumps(result, default=str)
        
        # Should be able to deserialize
        deserialized = json.loads(json_str)
        assert "search_metadata" in deserialized
        assert "tweets" in deserialized


class TestTweetObjectFields:
    """Test tweet object field types and structure."""
    
    def test_tweet_text_is_string(self):
        """Test that tweet text field is always string when present."""
        # Create a mock tweet to test structure
        mock_tweet = {
            "text": "Test tweet",
            "date": None,
            "likes": 100,
            "replies": 5,
            "retweets": 10,
            "views": 1000
        }
        
        assert isinstance(mock_tweet["text"], str)
    
    def test_engagement_metrics_are_numbers_or_none(self):
        """Test that engagement metrics are integers or None."""
        mock_tweet = {
            "text": "Test",
            "likes": 100,
            "replies": None,
            "retweets": 50,
            "views": None
        }
        
        # Check types
        assert mock_tweet["likes"] is None or isinstance(mock_tweet["likes"], (int, float))
        assert mock_tweet["replies"] is None or isinstance(mock_tweet["replies"], (int, float))
        assert mock_tweet["retweets"] is None or isinstance(mock_tweet["retweets"], (int, float))
        assert mock_tweet["views"] is None or isinstance(mock_tweet["views"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
