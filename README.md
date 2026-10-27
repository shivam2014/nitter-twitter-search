<p align="center">
  <img src="assets/readme/hero.svg" width="100%" alt="nitter-search: public X/Twitter posts without an API key. Mirrors fail; the search doesn't. A real run shows a rate-limited mirror, a challenge-gated mirror, and one answering through the browser.">
</p>

<p align="center">
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-1E2530?style=flat-square">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-1E2530?style=flat-square">
  <img alt="Tests 155 offline" src="https://img.shields.io/badge/tests-155%20offline-1E2530?style=flat-square">
  <img alt="MCP server" src="https://img.shields.io/badge/MCP-server-FF6B5E?style=flat-square">
</p>

Public Nitter mirrors are volunteer-run and they die constantly. Most scrapers
break when that happens, because a mirror URL is baked into the code. This one
discovers mirrors at runtime, prefers the cheapest transport that works, falls
back across instances, and remembers which ones failed.

Three ways in: MCP tools for agents, a CLI for scripts, a Python function for
everything else.

## What a call looks like

Trimmed from a real run (`--query "mars rover" --limit 3 --stats`):

```json
{
  "search_metadata": {
    "user": null,
    "query": "mars rover",
    "mirror_used": "https://nitter.netbub.com",
    "method": "browser",
    "total": 3,
    "error": null,
    "instances_tried": [
      {"url": "https://nitter.netbub.com", "ok": true, "method": "browser", "error": null}
    ]
  },
  "tweets": [
    {
      "id": "2114976333751025928",
      "url": "https://nitter.netbub.com/engineers_feed/status/2114976333751025928#m",
      "text": "Japan's MMX spacecraft just left Earth for Phobos, Mars's tiny, lumpy, mysterious moon...",
      "date": "2026-10-27T07:03:00Z",
      "author": "engineers_feed",
      "likes": 11
    }
  ]
}
```

`method` says where the data came from. `rss` is the fast path and leaves counts
`null`; `browser` renders the page and fills them in. `instances_tried` is the
receipt — read it before believing an empty result.

Every tweet carries `id`, `url`, `text`, `date` (ISO 8601 UTC), `author`,
`author_name`, `likes`, `replies`, `retweets`, `views`, `is_retweet`,
`retweeted_by`, `quote`, `pinned`, and `media` URLs.

## Install

```bash
git clone https://github.com/shivam2014/nitter-twitter-search.git
cd nitter-twitter-search
pip install -e .
```

Optional, for mirrors that fingerprint the browser:

```bash
pip install -e '.[camoufox]' && camoufox fetch
```

Without Camoufox it still works: it falls back to Playwright's Chromium, then to
an installed Google Chrome, then to RSS-only mode.

## Use

### As MCP tools

```bash
opencode mcp add nitter --global -- "$(command -v nitter-search-mcp)"
```

Three tools appear: `user_tweets` (a timeline, ~2s), `search_tweets`
(keywords, dates, filters), and `list_nitter_instances`. The server keeps a warm
browser and a warm instance list between calls.

### From the shell

```bash
nitter-search --user NASA --limit 5
nitter-search --user elonmusk --query tesla --since 2026-10-01
nitter-search --query "mars rover" --filter media --min-faves 100 --stats
nitter-search --check                 # which mirrors answer right now
```

`--text` prints one tweet per line, `--ndjson` one JSON object per line,
`--instance URL` pins a mirror. Output is JSON on stdout, diagnostics on stderr.

| Exit code | Meaning |
|-----------|---------|
| `0` | Tweets returned |
| `1` | Every mirror failed — run `--check` |
| `2` | Protected or missing account |
| `3` | No results for that query or range |

### From Python

```python
from nitter_search import search_tweets

result = search_tweets(user="NASA", limit=10)
for tweet in result["tweets"]:
    print(tweet["date"], tweet["text"])
```

### As an agent skill

Point an agent at [`SKILL.md`](SKILL.md). It documents the tool calls, the
result envelope, and the failure modes worth retrying — the MCP server is the
same package, so both paths share the fallback logic.

## Why it holds up

<p align="center">
  <img src="assets/readme/flow.svg" width="100%" alt="Four stages: normalise the request, discover healthy mirrors from status.d420.de with a six hour cache, try RSS first and the browser on challenge, return the envelope with the instances tried. Failures sink an instance for fifteen minutes.">
</p>

- **Discovery, not hard-coding.** Healthy mirrors come from `status.d420.de`,
  cached for six hours, filtered against known-dead hosts, and ranked by
  reliability. `nitter.net` has been offline since 2024 and is skipped by name.
- **RSS before browsers.** `/<user>/rss` is plain HTTP and answers in about two
  seconds. A browser only launches when the feed is challenge-gated or you asked
  for counts.
- **Challenge pages are not failures.** Anubis, "Gandalf" and Cloudflare gates
  are detected, cleared in a browser, and the resulting cookies are reused.
- **Session memory.** An instance that failed in the last fifteen minutes sinks
  in the queue, so repeated calls get faster instead of retrying dead mirrors.
- **Results are verified.** Some mirrors ignore the query and answer with a
  generic timeline; every token of the query is checked against the tweet before
  it is returned.
- **Honest diagnostics.** `search_metadata.instances_tried` says which mirror was
  tried, over which transport, and why it was dropped.

## Filters

Passed straight to Nitter's query string, server-side:

```bash
nitter-search --query "mars" --filter media --min-faves 100 --min-retweets 10
```

| Filter | Flag | Notes |
|--------|------|-------|
| Date range | `--since`, `--until` | `YYYY-MM-DD`, inclusive |
| Media | `--filter media` | images, video, GIFs |
| Links | `--filter links` | tweets containing URLs |
| Quotes | `--filter quotes` | quote tweets |
| Replies | `--filter replies` | reply tweets |
| Minimum likes | `--min-faves N` | |
| Minimum retweets | `--min-retweets N` | |
| Minimum replies | `--min-replies N` | |

Full parameter list: [docs/api.md](docs/api.md). Mirror behaviour and status
handling: [docs/nitter-instances.md](docs/nitter-instances.md).

## Limits

- Public mirrors rate limit hard. A single call can return nothing; retry or pin
  another instance.
- Some mirrors disable search entirely ("Search has been disabled due to abuse").
  Those are skipped and the timeline endpoints still work.
- Protected accounts, deleted tweets, and age-restricted media are unreachable.
- RSS returns the newest ~20 items. Ask for more and the browser path paginates.
- This scrapes public pages through third-party mirrors. Use it for research and
  monitoring at a human pace, not for bulk harvesting.

## Development

```bash
./run_tests.sh          # 155 offline tests, under a second
nitter-search --check   # live mirror health
```

Tests never touch the network: HTTP payloads come from `tests/fixtures/`,
captured from live instances, and browser calls are faked. See
[tests/TESTING.md](tests/TESTING.md) for the fixture map and why v1's
"73 passing tests" were passing without testing anything.

```
src/nitter_search/
├── urls.py        URL building and validation
├── parse.py       HTML/RSS parsing, counts, dates, page classification
├── instances.py   discovery, health memory, probing
├── transport.py   http_get + BrowserSession (camoufox → chromium → chrome)
├── search.py      orchestration and the result envelope
├── mcp_server.py  stdio MCP server
└── cli.py         command line entry point
```

## License

MIT. See [LICENSE](LICENSE).

Built as an agent skill; the MCP server and CLI came later. Originally created
with [Hermes Agent](https://github.com/NousResearch/hermes-agent), rewritten for
v2 after public Nitter instances changed shape.
