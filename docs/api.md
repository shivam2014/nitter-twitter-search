# API Documentation

## Module: `nitter_search.browser_scraper`

### Function: `scrape_user_tweets_camoufox()`

Search and scrape tweets from a Twitter/X user via Nitter using Camoufox anti-detect browser.

#### Signature

```python
def scrape_user_tweets_camoufox(
    username: str,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_tweets: int = 100,
    mirror: str = "https://nitter.net"
) -> Dict[str, Any]
```

#### Parameters

- **username** (str, required): Twitter username without the @ symbol
- **query** (str, optional): Search query to filter tweets by keyword
- **start_date** (str, optional): Start date in YYYY-MM-DD format
- **end_date** (str, optional): End date in YYYY-MM-DD format
- **max_tweets** (int, optional): Maximum number of tweets to return (default: 100)
- **mirror** (str, optional): Nitter instance URL (default: "https://nitter.net")

#### Returns

Dict containing:

```python
{
    "search_metadata": {
        "query": str | None,        # Search query used
        "user": str,                # Username searched
        "private_profile": bool,    # True if profile is private
        "error": str | None,        # Error message if any occurred
        "timestamp": str,           # ISO 8601 timestamp of search
        "mirror_used": str,         # Nitter instance URL used
        "method": str               # Scraping method ("camoufox")
    },
    "tweets": List[Dict[str, Any]]  # List of tweet data
}
```

Each tweet in the list contains:

```python
{
    "text": str,            # Tweet text content
    "date": str | None,     # Tweet date (if available)
    "likes": int | None,    # Like count
    "replies": int | None,  # Reply count
    "retweets": int | None, # Retweet count
    "views": int | None     # View count
}
```

#### Example

```python
from nitter_search.browser_scraper import scrape_user_tweets_camoufox

result = scrape_user_tweets_camoufox(
    username="NASA",
    query="Mars",
    start_date="2026-03-01",
    end_date="2026-03-31",
    max_tweets=20
)

# Check for errors
if result['search_metadata'].get('error'):
    print(f"Error: {result['search_metadata']['error']}")

# Check for private profile
if result['search_metadata'].get('private_profile'):
    print("Profile is private")

# Access tweets
for tweet in result['tweets']:
    print(tweet['text'])
```

#### Exceptions

May raise `Exception` if browser automation fails. Error details will be included in the return value's `search_metadata.error` field.

## CLI: `nitter-search`

Command-line interface for searching tweets.

### Usage

```bash
nitter-search --user USERNAME [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--user USERNAME` | `-u` | Twitter username (required) |
| `--query QUERY` | `-q` | Search query filter |
| `--start-date DATE` | | Start date (YYYY-MM-DD) |
| `--end-date DATE` | | End date (YYYY-MM-DD) |
| `--max-tweets N` | `-n` | Maximum tweets to return (default: 100) |
| `--mirror URL` | `-m` | Nitter instance URL |
| `--help` | `-h` | Show help message |

### Examples

```bash
# Basic search
nitter-search --user "NASA" --max-tweets 10

# With query filter
nitter-search --user "elonmusk" --query "AI"

# Date range
nitter-search --user "NASA" --start-date "2026-03-23" --end-date "2026-03-24"

# Custom Nitter instance
nitter-search --user "NASA" --mirror "https://nitter.moe"
```
