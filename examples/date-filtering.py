#!/usr/bin/env python3
"""Date filtering example - search tweets within a specific date range."""

import sys
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import scrape_user_tweets_camoufox


def main():
    """Example: Search tweets from March 23-24, 2026."""
    
    print("Searching for tweets between 2026-03-23 and 2026-03-24...\n")
    
    result = scrape_user_tweets_camoufox(
        username="NASA",
        start_date="2026-03-23",
        end_date="2026-03-24",
        max_tweets=10
    )
    
    print(f"Search metadata: {result['search_metadata']}")
    print(f"\nFound {len(result['tweets'])} tweets in date range:\n")
    
    for i, tweet in enumerate(result['tweets'], 1):
        print(f"{i}. {tweet['text'][:150]}...")
        print()


if __name__ == "__main__":
    main()
