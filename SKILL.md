---
name: nitter-twitter-search
description: Search Twitter/X via Nitter mirrors with automatic instance discovery and browser fallback. Returns structured JSON for agents. Use when you need recent tweets, a user timeline, date-scoped keyword searches, or engagement data without an API key.
version: 2.0.0
author: shivam2014
license: MIT
metadata:
  tags: [twitter, nitter, ai-agents, web-scraping, camouflage, search, mcp]
---

# Nitter Twitter Search

Read public X/Twitter posts through Nitter mirrors. No API key, no login, no
account. Built to survive the fact that public mirrors disappear, rate limit, or
hide behind proof-of-work gates.

## How it decides where to look

1. **Instance discovery.** Healthy mirrors come from `status.d420.de`, cached for
   six hours, merged with a seed list. Nothing is hard-coded to a mirror that
   died last year.
2. **Cheapest transport first.** `/<user>/rss` is plain HTTP and answers in about
   two seconds. Only when the feed is challenge-gated, or you asked for
   engagement counts, does it launch a browser.
3. **Browser fallback.** Camoufox if installed, otherwise Playwright with bundled
   Chromium, otherwise your installed Google Chrome. The browser clears the
   JavaScript proof-of-work gate and the cookies are reused for later calls.
4. **Health memory.** An instance that failed in the last fifteen minutes sinks
   to the bottom of the queue, so repeated calls get faster, not slower.

## Install

```bash
git clone https://github.com/shivam2014/nitter-twitter-search.git
cd nitter-twitter-search
pip install -e .
```

Optional but recommended, for instances that fingerprint the browser:

```bash
pip install -e '.[camoufox]'
camoufox fetch
```

If neither Camoufox nor a Chromium is present, the tool still works for RSS
endpoints and says so clearly instead of hanging.

## Option A: MCP tools (best for agents)

The package ships a stdio MCP server. Register it once:

```bash
opencode mcp add nitter --global -- nitter-search-mcp
```

That yields three native tools:

| Tool | Use it for |
|------|------------|
| `nitter_user_tweets` | A person's timeline, newest first. Fastest path. |
| `nitter_search_tweets` | Keyword, date-scoped, or filtered search. |
| `nitter_list_nitter_instances` | Which mirrors are reachable right now. |

The server keeps one browser alive between calls, so the second search is much
faster than the first. It also remembers which instances work.

## Option B: CLI

```bash
nitter-search --user NASA --limit 10
nitter-search --query "mars rover" --since 2026-10-01 --until 2026-10-26
nitter-search --user elonmusk --query AI --stats --limit 5
nitter-search --check
nitter-search --list-instances
```

Exit codes: `0` success, `1` transport failure, `2` protected or missing account,
`3` no results.

## Option C: Python

```python
from nitter_search import search_tweets

result = search_tweets(user="NASA", limit=10)
for tweet in result["tweets"]:
    print(tweet["date"], tweet["text"])
```

Set `with_stats=True` to collect likes, replies, retweets and views.

## Result shape

```json
{
  "search_metadata": {
    "user": "NASA",
    "query": null,
    "since": null,
    "until": null,
    "limit": 10,
    "timestamp": "2026-10-26T15:22:54Z",
    "mirror_used": "https://nitter.netbub.com",
    "method": "rss",
    "total": 10,
    "private_profile": false,
    "error": null,
    "instances_tried": [{"url": "https://nitter.netbub.com", "ok": true, "method": "rss"}]
  },
  "tweets": [
    {
      "id": "2114484649430798432",
      "url": "https://nitter.netbub.com/NASA/status/2114484649430798432",
      "text": "Tweet text",
      "date": "2026-10-25T22:30:00Z",
      "author": "NASA",
      "author_name": "NASA",
      "likes": null,
      "replies": null,
      "retweets": null,
      "views": null,
      "is_retweet": false,
      "retweeted_by": null,
      "quote": null,
      "pinned": false,
      "media": []
    }
  ]
}
```

`method: "rss"` means counts are `null` by design. `method: "browser"` fills them.

## Error handling

Read `search_metadata.error` first, then `instances_tried` to see why each mirror
was dropped. The common ones:

| Symptom | Meaning | What to do |
|---------|---------|-----------|
| `challenge` | Proof-of-work or Cloudflare gate | Retry; it clears once the browser solves it |
| `rate limited` | Mirror exhausted its backend tokens | Wait, or let health memory skip it |
| `Search is disabled` | Mirror turned search off | Use `--user` (timeline) instead |
| `No results` | Terminal: bad handle, empty range, or deleted content | Widen the dates or check the handle |
| `Every instance failed` | All candidates refused | `nitter-search --check` |

## Limits

- Public mirrors are best-effort. Treat any single call as flaky.
- RSS returns at most one page (about twenty tweets). Ask for more and the tool
  switches to the browser to paginate.
- Date filters are server-side and inclusive per Twitter's semantics, so an
  `until` bound excludes that day's later tweets. Widen by a day when in doubt.
- Protected accounts, deleted tweets, and age-restricted media are not reachable.

## See also

- [README.md](README.md) — overview, install, examples
- [docs/api.md](docs/api.md) — full Python and CLI reference
- [docs/filters-reference.md](docs/filters-reference.md) — Nitter filter syntax
- [docs/nitter-instances.md](docs/nitter-instances.md) — how discovery works
