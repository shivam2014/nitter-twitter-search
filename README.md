# Nitter Twitter Search

AI agent skill for searching Twitter/X via Nitter with Camoufox anti-detect browser. Designed for use with AI coding agents like Claude Code, Hermes Agent, and similar tools.

## Features

- 🔍 **Search tweets** from specific users or general queries
- 📅 **Date filtering** - Search tweets between specific dates
- 🎯 **Advanced filters** - Min favorites, replies, retweets support
- 🛡️ **Anti-detection** - Uses Camoufox to bypass bot detection
- 🌐 **Multiple Nitter instances** - Fallback support for reliability
- 🤖 **Agent-friendly** - Structured JSON output for AI consumption

## Installation

### Option 1: pip install (Recommended)

```bash
pip install nitter-twitter-search
```

### Option 2: From GitHub

```bash
pip install git+https://github.com/shivam2014/nitter-twitter-search.git
```

### Option 3: Local development

```bash
git clone https://github.com/shivam2014/nitter-twitter-search.git
cd nitter-twitter-search
pip install -e .
```

## Prerequisites

Install Playwright browsers (required by Camoufox):

```bash
playwright install
```

## Quick Start

### CLI Usage

```bash
# Search user's tweets
nitter-search --user "NASA" --max-tweets 10

# Search with query filter
nitter-search --user "elonmusk" --query "AI" --max-tweets 20

# Date range search (since March 23, until March 24, 2026)
nitter-search --user "NASA" --start-date "2026-03-23" --end-date "2026-03-24"

# Advanced filters
nitter-search --user "NASA" --min-faves 100 --min-retweets 50
```

### Python Usage

```python
from nitter_search.browser_scraper import scrape_user_tweets_camoufox

# Basic search
result = scrape_user_tweets_camoufox(
    username="NASA",
    max_tweets=10
)

print(result['tweets'])

# Date range search
result = scrape_user_tweets_camoufox(
    username="elonmusk",
    query="AI",
    start_date="2026-03-23",
    end_date="2026-03-24",
    max_tweets=20
)

# Access metadata
print(f"Found {len(result['tweets'])} tweets")
print(f"Search time: {result['search_metadata']['timestamp']}")
```

### AI Agent Integration (Claude Code, Hermes Agent, etc.)

Add this to your skills directory:

```bash
cd ~/.claude/skills  # or your agent's skill directory
git clone https://github.com/shivam2014/nitter-twitter-search.git
```

Then load the skill and use it in your prompts. See `SKILL.md` for detailed integration instructions.

## Filter Reference

Nitter supports powerful search filters via URL parameters:

| Filter | Format | Example |
|--------|--------|---------|
| Date range | `since=YYYY-MM-DD` & `until=YYYY-MM-DD` | `since=2026-03-23&until=2026-03-24` |
| Min favorites | `min_faves=N` | `min_faves=100` |
| Min retweets | `min_retweets=N` | `min_retweets=50` |
| Min replies | `min_replies=N` | `min_replies=10` |
| Has media | `filter=media` | Images, videos, GIFs |
| Has links | `filter=links` | Tweets with URLs |
| Has quotes | `filter=quotes` | Quote tweets |

### Example: Complex Search

```python
result = scrape_user_tweets_camoufox(
    username="NASA",
    query="Mars",
    start_date="2026-03-01",
    end_date="2026-03-31",
    max_tweets=50
)
```

This constructs: `https://nitter.net/NASA/search?f=tweets&q=Mars&since=2026-03-01&until=2026-03-31`

## Output Format

The scraper returns structured JSON:

```json
{
  "search_metadata": {
    "query": "AI",
    "user": "elonmusk",
    "private_profile": false,
    "timestamp": "2026-03-24T20:30:00Z",
    "mirror_used": "https://nitter.net",
    "method": "camoufox"
  },
  "tweets": [
    {
      "text": "Tweet content here...",
      "date": null,
      "likes": 1234,
      "replies": 56,
      "retweets": 789,
      "views": 12345
    }
  ]
}
```

## Nitter Instances

The tool supports multiple Nitter instances for reliability:

- `https://nitter.net` (default)
- `https://nitter.moe`
- `https://nitter.pussthecat.org`
- `https://nitter.snopyta.org`

See `docs/nitter-instances.md` for a complete list.

## Troubleshooting

### "Camoufox library not installed"

```bash
pip install camoufox playwright
playwright install
```

### No tweets found

1. Check if the user has public tweets
2. Try different date ranges
3. Switch Nitter instance: `--mirror "https://nitter.moe"`
4. Some users may have deleted old tweets

### Rate limiting

Nitter instances may rate limit. Try:
- Adding delays between requests
- Switching to a different Nitter instance
- Reducing the number of requests

### Private accounts

The tool detects private accounts and returns:
```json
{
  "search_metadata": {
    "private_profile": true,
    "error": "Profile is private or unavailable"
  },
  "tweets": []
}
```

## Development

### Running tests

```bash
pytest tests/
```

### Code formatting

```bash
black src/
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Related Tools

- [Camoufox](https://github.com/0xpadawan/camoufox) - Anti-detect browser automation
- [Nitter](https://github.com/zedeus/nitter) - Twitter frontend alternative
- [Playwright](https://playwright.dev) - Browser automation framework

## Support

For issues and questions, please open a GitHub issue: https://github.com/shivam2014/nitter-twitter-search/issues
