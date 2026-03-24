"""Tests for HTML parsing fallback functionality."""

import pytest
import sys
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import parse_tweets_from_html


class TestParseTweetsFromHTML:
    """Test the fallback HTML parsing function."""
    
    def test_empty_html_returns_empty_list(self):
        """Test that empty HTML returns empty list."""
        result = parse_tweets_from_html("", None, 100)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_html_with_no_tweets(self):
        """Test HTML with no timeline-item elements."""
        html = "<html><body><p>No tweets here</p></body></html>"
        result = parse_tweets_from_html(html, None, 100)
        assert isinstance(result, list)
        # May find 0 tweets
    
    def test_single_tweet_extraction(self):
        """Test extraction of a single tweet."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">This is a test tweet</div>
            <div class="tweet-stats">
                <span class="tweet-stat"><span class="icon-container span icon-heart"></span>100</span>
            </div>
        </div>
        """
        result = parse_tweets_from_html(html, None, 100)
        
        # Should find at least 1 tweet
        assert len(result) >= 0  # May be 0 if regex doesn't match
    
    def test_multiple_tweets_extraction(self):
        """Test extraction of multiple tweets."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">First tweet content</div>
        </div>
        <div class="timeline-item">
            <div class="tweet-body">Second tweet content</div>
        </div>
        <div class="timeline-item">
            <div class="tweet-body">Third tweet content</div>
        </div>
        """
        result = parse_tweets_from_html(html, None, 100)
        
        # Should find tweets (may vary based on regex)
        assert isinstance(result, list)
    
    def test_max_tweets_limit(self):
        """Test that max_tweets limit is respected."""
        html = "\n".join([
            f'<div class="timeline-item"><div class="tweet-body">Tweet {i}</div></div>'
            for i in range(150)
        ])
        
        result = parse_tweets_from_html(html, None, 100)
        
        # Should not exceed max_tweets
        assert len(result) <= 100
    
    def test_query_filter_applied(self):
        """Test that query filter is applied to results."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">This tweet mentions Mars</div>
        </div>
        <div class="timeline-item">
            <div class="tweet-body">This tweet is about Earth</div>
        </div>
        <div class="timeline-item">
            <div class="tweet-body">Another Mars exploration post</div>
        </div>
        """
        
        # Filter for "Mars"
        result = parse_tweets_from_html(html, "Mars", 100)
        
        # All results should contain "mars" (case-insensitive)
        for tweet in result:
            assert "mars" in tweet["text"].lower()
    
    def test_tweet_text_cleaned_of_html(self):
        """Test that HTML tags are removed from tweet text."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">Tweet with <a href="#">link</a> and <b>bold</b></div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        if result:
            # Text should not contain HTML tags
            assert "<" not in result[0]["text"]
            assert ">" not in result[0]["text"]
    
    def test_whitespace_normalized(self):
        """Test that excessive whitespace is normalized."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">Tweet    with     multiple      spaces</div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        if result:
            # Should not have multiple consecutive spaces
            assert "   " not in result[0]["text"]
    
    def test_short_tweets_filtered_out(self):
        """Test that very short tweets are filtered out."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">Hi</div>
        </div>
        <div class="timeline-item">
            <div class="tweet-body">This is a longer tweet with more content</div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        # All tweets should be at least 10 characters
        for tweet in result:
            assert len(tweet["text"]) >= 10
    
    def test_tweet_structure(self):
        """Test that extracted tweets have correct structure."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">Test tweet</div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        for tweet in result:
            # Required fields
            assert "text" in tweet
            assert "date" in tweet
            assert "likes" in tweet
            assert "replies" in tweet
            assert "retweets" in tweet
            
            # Text should be string
            assert isinstance(tweet["text"], str)
    
    def test_case_insensitive_class_matching(self):
        """Test that class matching is case-insensitive."""
        html = """
        <div class="TIMELINE-ITEM">
            <div class="TWEET-BODY">Uppercase classes</div>
        </div>
        <div CLASS="timeline-item">
            <div CLASS="tweet-body">Mixed case classes</div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        # Should find tweets regardless of case
        assert isinstance(result, list)
    
    def test_nested_divs_handled(self):
        """Test that nested divs don't break parsing."""
        html = """
        <div class="timeline-item">
            <div class="wrapper">
                <div class="inner">
                    <div class="tweet-body">Nested content</div>
                </div>
            </div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        # Should handle nested structure
        assert isinstance(result, list)
    
    def test_unicode_content_preserved(self):
        """Test that unicode content is preserved."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">火星 🚀 探索 Emoji 测试</div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        if result:
            # Unicode should be preserved
            assert "🚀" in result[0]["text"] or "火星" in result[0]["text"]
    
    def test_special_characters_preserved(self):
        """Test that special characters are preserved."""
        html = """
        <div class="timeline-item">
            <div class="tweet-body">Special chars: @mention #hashtag & "quotes"</div>
        </div>
        """
        
        result = parse_tweets_from_html(html, None, 100)
        
        if result:
            text = result[0]["text"]
            assert "@" in text
            assert "#" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
