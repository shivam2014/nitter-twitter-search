#!/usr/bin/env python3
"""Basic Twitter search example using nitter-twitter-search."""

import sys
sys.path.insert(0, '../src')

from nitter_search.browser_scraper import scrape_user_tweets_camoufox


def main():
    """Example: Search NASA's recent tweets."""
    
    print("Searching for NASA tweets...\n")
    
    result = scrape_user_tweets_camoufox(
        username="NASA",
        max_tweets=5
    )
    
    # Check for errors
    if result['search_metadata'].get('error'):
        print(f"Error: {result['search_metadata']['error']}")
        return
    
    # Check for private profile
    if result['search_metadata'].get('private_profile'):
        print("Profile is private")
        return
    
    # Display tweets
    print(f"Found {len(result['tweets'])} tweets:\n")
    
    for i, tweet in enumerate(result['tweets'], 1):
        print(f"{i}. {tweet['text'][:200]}...")
        if tweet.get('likes'):
            print(f"   Likes: {tweet['likes']} | Retweets: {tweet.get('retweets', 0)}")
        print()


if __name__ == "__main__":
    main()
