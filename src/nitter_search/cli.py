"""CLI entry point for twitter-search tool."""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any


def build_search_url(
    username: Optional[str],
    query: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    mirror: str
) -> str:
    """
    Build Nitter search URL with server-side date filters.
    
    Nitter uses URL parameters for filtering:
    - f=tweets for tweets only
    - q=QUERY for text search
    - since=YYYY-MM-DD for start date
    - until=YYYY-MM-DD for end date
    """
    from urllib.parse import quote, urlencode
    
    # Build query string (text to search for)
    search_query = (query or "").strip()
    
    # Determine base URL path
    if username:
        base_path = f"{mirror}/{username}/search"
    else:
        base_path = f"{mirror}/search"
    
    # Build parameters
    params = {
        "f": "tweets",  # Filter for tweets only
        "q": search_query if search_query else ""
    }
    
    # Add date filters as URL parameters (not query syntax)
    if start_date:
        params["since"] = start_date
    if end_date:
        params["until"] = end_date
    
    return f"{base_path}?{urlencode(params)}"


def search_twitter(
    query: str,
    user: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_tweets: int = 100,
    mirror: str = "https://nitter.net"
) -> Dict[str, Any]:
    """
    Search Twitter via Nitter mirrors using Camoufox browser automation.
    """
    try:
        print(f"Starting Camoufox scrape...", file=sys.stderr)
        
        # Build URL with date filters
        search_url = build_search_url(user, query, start_date, end_date, mirror)
        print(f"URL: {search_url}", file=sys.stderr)
        
        from twitter_search.browser_scraper_camoufox import scrape_user_tweets_camoufox
        
        result = scrape_user_tweets_camoufox(
            username=user or query,
            query=query,
            start_date=start_date,
            end_date=end_date,
            max_tweets=max_tweets,
            mirror=mirror
        )
        
        return result
        
    except ImportError:
        print("camoufox not available", file=sys.stderr)
        return {
            "search_metadata": {
                "query": query,
                "user": user,
                "start_date": start_date,
                "end_date": end_date,
                "timestamp": datetime.now().isoformat() + "Z",
                "mirror_used": mirror,
                "error": "camoufox not installed. Install with: pip3 install camoufox",
                "method": "failed"
            },
            "tweets": []
        }
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return {
            "search_metadata": {
                "query": query,
                "user": user,
                "start_date": start_date,
                "end_date": end_date,
                "timestamp": datetime.now().isoformat() + "Z",
                "mirror_used": mirror,
                "error": str(e),
                "method": "failed"
            },
            "tweets": []
        }


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Search Twitter/X via Nitter mirrors using Camoufox browser automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  twitter-search --user "NASA" --max-tweets 20
  twitter-search --user "elonmusk" --query "tesla" --max-tweets 30
  twitter-search --user "cirnosad" --start-date 2026-03-18 --end-date 2026-03-18
  twitter-search --query "artificial intelligence" --max-tweets 50
        """
    )
    
    # Required (one of)
    parser.add_argument("--query", type=str, default=None,
                        help="Search query text")
    parser.add_argument("--user", type=str, default=None,
                        help="Twitter username to search within")
    
    # Date range (server-side filtering via Nitter)
    parser.add_argument("--start-date", type=str, default=None,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="End date (YYYY-MM-DD)")
    
    # Output options
    parser.add_argument("--max-tweets", type=int, default=100,
                        help="Maximum tweets to fetch (default: 100)")
    parser.add_argument("--mirror", type=str, default="https://nitter.net",
                        help="Nitter mirror URL (default: https://nitter.net)")
    
    args = parser.parse_args()
    
    if not args.query and not args.user:
        parser.error("Either --query or --user must be provided")
    
    result = search_twitter(
        query=args.query or "",
        user=args.user,
        start_date=args.start_date,
        end_date=args.end_date,
        max_tweets=args.max_tweets,
        mirror=args.mirror
    )
    
    output_json = json.dumps(result, indent=2, default=str)
    print(output_json)
    
    if result["search_metadata"].get("error"):
        sys.exit(1)
    elif result["search_metadata"].get("private_profile"):
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
