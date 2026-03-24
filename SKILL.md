---
name: nitter-twitter-search
description: Search Twitter/X via Nitter with Camoufox anti-detect browser. AI agent skill for retrieving tweets by user, query, and date range.
version: 1.0.0
author: shivam2014
license: MIT
metadata:
  hermes:
    tags: [twitter, nitter, ai-agents, web-scraping, camoufox, search]
---

# Nitter Twitter Search Skill

AI agent skill for searching Twitter/X via Nitter with Camoufox anti-detect browser. Returns structured JSON data suitable for AI consumption.

## Installation

### For AI Agents (Claude Code, Hermes Agent, etc.)

```bash
# Clone to your skills directory
cd ~/.claude/skills  # or your agent's skill path
git clone https://github.com/shivam2014/nitter-twitter-search.git nitter-twitter-search
```

### Install Dependencies

```bash
cd nitter-twitter-search
pip install -e .
playwright install  # Required for browser automation
```

## Usage Patterns

### 1. Search User Tweets

**Goal:** Get recent tweets from a specific user

```python
from nitter_search.browser_scraper import scrape_user_tweets_camoufox

result = scrape_user_tweets_camoufox(
    username="NASA",
    max_tweets=10
)

# Process results
for tweet in result['tweets']:
    print(tweet['text'])
```

**Returns:**
```json
{
  "search_metadata": {
    "query": null,
    "user": "NASA",
    "private_profile": false,
    "timestamp": "2026-03-24T20:30:00Z",
    "mirror_used": "https://nitter.net",
    "method": "camoufox"
  },
  "tweets": [
    {
      "text": "Tweet content...",
      "likes": 1234,
      "replies": 56,
      "retweets": 789,
      "views": 12345
    }
  ]
}
```

### 2. Search with Query Filter

**Goal:** Find tweets containing specific keywords from a user

```python
result = scrape_user_tweets_camoufox(
    username="elonmusk",
    query="AI",
    max_tweets=20
)
```

This searches Elon Musk's tweets for those containing "AI".

### 3. Date Range Search

**Goal:** Get tweets from a specific time period

```python
result = scrape_user_tweets_camoufox(
    username="NASA",
    start_date="2026-03-23",
    end_date="2026-03-24",
    max_tweets=50
)
```

**URL constructed:** `https://nitter.net/NASA/search?f=tweets&q=&since=2026-03-23&until=2026-03-24`

**Date format:** `YYYY-MM-DD` (ISO 8601)

### 4. Advanced Filters

**Goal:** Filter by engagement metrics

```python
# Note: Nitter URL parameters for min_faves, min_retweets, etc.
# These are passed via the mirror URL if needed

result = scrape_user_tweets_camoufox(
    username="NASA",
    query="Mars mission",
    start_date="2026-01-01",
    end_date="2026-12-31",
    max_tweets=100
)

# Filter results in Python by engagement
high_engagement = [
    t for t in result['tweets']
    if (t.get('likes') or 0) > 1000
]
```

## API Reference

### `scrape_user_tweets_camoufox()`

Main function for scraping tweets via Camoufox browser automation.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `username` | str | Yes | - | Twitter username (without @) |
| `query` | str | No | None | Search query to filter tweets |
| `start_date` | str | No | None | Start date (YYYY-MM-DD) |
| `end_date` | str | No | None | End date (YYYY-MM-DD) |
| `max_tweets` | int | No | 100 | Maximum tweets to return |
| `mirror` | str | No | "https://nitter.net" | Nitter instance URL |

**Returns:**

```python
{
    "search_metadata": {
        "query": str | None,        # Search query used
        "user": str,                # Username searched
        "private_profile": bool,    # True if profile is private
        "error": str | None,        # Error message if any
        "timestamp": str,           # ISO 8601 timestamp
        "mirror_used": str,         # Nitter instance used
        "method": str               # Scraping method ("camoufox")
    },
    "tweets": [
        {
            "text": str,            # Tweet text content
            "date": str | None,     # Tweet date (if available)
            "likes": int | None,    # Like count
            "replies": int | None,  # Reply count
            "retweets": int | None, # Retweet count
            "views": int | None     # View count
        }
    ]
}
```

**Raises:**

- `Exception` if browser automation fails (returned in error field)

## Error Handling

### Private Profile Detection

```python
result = scrape_user_tweets_camoufox(username="private_user")

if result['search_metadata'].get('private_profile'):
    print("This account is private")
    return []

# Process public tweets
return result['tweets']
```

### Nitter Instance Fallback

```python
instances = [
    "https://nitter.net",
    "https://nitter.moe",
    "https://nitter.pussthecat.org"
]

for mirror in instances:
    result = scrape_user_tweets_camoufox(
        username="NASA",
        mirror=mirror,
        max_tweets=10
    )
    
    if result['tweets']:
        break  # Success!
```

### Timeout Handling

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Search took too long")

# Set 30-second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

try:
    result = scrape_user_tweets_camoufox(username="NASA")
    signal.alarm(0)  # Cancel timeout
except TimeoutError:
    result = {"tweets": [], "search_metadata": {"error": "Timeout"}}
```

## CLI Usage (for testing)

```bash
# Install package first
pip install -e .

# Run searches via CLI
nitter-search --user "NASA" --max-tweets 10
nitter-search --user "elonmusk" --query "AI" --start-date "2026-03-01"
```

## Integration Examples

### Claude Code Skill Usage

Add to your `.claude/skills/nitter-twitter-search/SKILL.md` (this file). Then in your prompts:

```
Use the nitter-twitter-search skill to find recent tweets from @NASA about Mars missions.
```

The agent will automatically load and use the skill.

### Hermes Agent Integration

```python
# In your agent code
from nitter_search.browser_scraper import scrape_user_tweets_camoufox

def get_twitter_context(username: str, topic: str = None) -> list:
    """Get relevant tweets for context"""
    result = scrape_user_tweets_camoufox(
        username=username,
        query=topic,
        max_tweets=20
    )
    
    return [t['text'] for t in result['tweets'][:5]]
```

## Limitations

1. **Rate limiting:** Nitter instances may rate limit frequent requests
2. **No real-time data:** Nitter caches data, may not be instant
3. **Private accounts:** Cannot access private profile tweets
4. **Deleted tweets:** Not recoverable if deleted from Twitter
5. **Browser required:** Needs Playwright browsers installed
6. **Date accuracy:** Tweet dates may not always be extracted

## Best Practices

1. **Cache results:** Store tweet data to avoid repeated scraping
2. **Respect rate limits:** Add delays between requests (>5 seconds)
3. **Use multiple mirrors:** Have fallback Nitter instances ready
4. **Handle errors gracefully:** Always check for `private_profile` and `error` fields
5. **Limit max_tweets:** Don't request more than needed (default 100 is reasonable)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Camoufox not installed" | `pip install camoufox playwright && playwright install` |
| No tweets found | Check if user has public tweets, try different date range |
| Rate limited | Switch Nitter mirror or add delays between requests |
| Private profile | Tool correctly detects this; cannot scrape private accounts |
| Browser errors | Run `playwright install --force` to reinstall browsers |

## See Also

- [README.md](README.md) - Full documentation and examples
- [docs/filters-reference.md](docs/filters-reference.md) - Nitter filter syntax
- [docs/nitter-instances.md](docs/nitter-instances.md) - Available Nitter mirrors
- [examples/](examples/) - Usage example scripts

## License

MIT License - Free for open and closed source use.
