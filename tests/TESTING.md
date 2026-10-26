# Testing

The suite runs offline. Every network call is monkeypatched and every payload
comes from `tests/fixtures/`, which holds pages and feeds captured from live
instances.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

or `./run_tests.sh`, which uses `.venv` when it exists.

## Layout

| File | Covers |
|------|--------|
| `test_urls.py` | URL construction, validation, filters, cursor encoding |
| `test_parse.py` | HTML/RSS extraction against fixtures, counts, dates, classification |
| `test_instances.py` | Discovery, caching, health memory, probing |
| `test_search.py` | Instance fallback, transport choice, dedupe/sort, error envelopes |
| `test_mcp.py` | JSON-RPC handshake, tool catalog, dispatch, error containment |
| `test_cli.py` | Output modes, exit codes, flag-to-request mapping, maintenance commands |

## Fixtures

| File | Source | What it proves |
|------|--------|----------------|
| `profile.html` | timeline page, 20 items | `.timeline-item` parsing, stats, cursor, pinned flag |
| `search.html` | search results, 17 items | multi-author results, inline mentions, hashtags |
| `user_rss.xml` | `/NASA/rss`, 20 items | `<link>` handling, `dc:creator`, `pubDate`, CDATA media |
| `challenge.html` | Anubis gate | challenge detection |

Refreshing a fixture is safe as long as its structure keeps the same shapes:

```bash
curl -sL https://nitter.netbub.com/NASA/rss -o tests/fixtures/user_rss.xml
```

## What is deliberately not tested

Live network calls. The transport layer is thin and its failure modes are
classified in `parse.classify_page`, which *is* tested. If you want a live check:

```bash
nitter-search --check
nitter-search --user NASA --limit 3 --no-browser
```

## Known trap from v1

The old suite called the real scraper and asserted only that a dict came back.
Every test passed because Camoufox was absent, so every call hit the
"not installed" branch. The suite now injects fakes, so a broken transport or
parser fails the run instead of silently passing.
