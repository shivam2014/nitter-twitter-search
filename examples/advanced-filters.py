#!/usr/bin/env python3
"""Advanced filtering example - query + date range + engagement filtering."""

import sys
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import scrape_user_tweets_camoufox


def main():
    """Example: Search with query filter and post-filter by engagement."""
    
    print("Searching for high-engagement NASA tweets about Mars...\n")
    
    # Get tweets with query and date filters
    result = scrape_user_tweets_camoufox(
        username="NASA",
        query="Mars",
        start_date="2026-01-01",
        end_date="2026-12-31",
        max_tweets=50
    )
    
    print(f"Total tweets found: {len(result['tweets'])}")
    
    # Filter by engagement (likes > 100)
    high_engagement = [
        t for t in result['tweets']
        if (t.get('likes') or 0) > 100
    ]
    
    print(f"High engagement tweets (>100 likes): {len(high_engagement)}\n")
    
    # Sort by likes
    sorted_tweets = sorted(high_engagement, key=lambda x: x.get('likes') or 0, reverse=True)
    
    for i, tweet in enumerate(sorted_tweets[:5], 1):
        print(f"{i}. ({tweet.get('likes', 0)} likes) {tweet['text'][:150]}...")
        print()


if __name__ == "__main__":
    main()
