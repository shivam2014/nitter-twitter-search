# Release notes (v2.0.0)

## Breaking changes

- `scrape_user_tweets_camoufox(..., mirror=...)` now defaults to `None`
  (auto-select) instead of the defunct `https://nitter.net`.
- `parse_tweets_from_html()` gained an `instance` argument; the old signature
  still works but URLs in results now point at the serving mirror.
- `nitter_search.cli.build_search_url()` was moved to `nitter_search.urls` with a
  new signature (instance first).

## New

- Runtime instance discovery with a 6-hour cache and 15-minute health memory.
- RSS fast path (no browser) for timelines; browser path only when needed.
- Browser backends: Camoufox, bundled Chromium, installed Chrome.
- Cursor pagination for `--limit` above 20.
- Engagement, author, quote, retweet, pinned and media fields in the result.
- `nitter-search-mcp` stdio MCP server with three tools.
- `--check`, `--list-instances`, `--text`, `--ndjson`, `--pretty`, `--stats`.

## Fixed

- CLI imported a module that never existed.
- Camoufox was driven through a non-existent `.start()` method.
- Default instance had been offline since 2024.
- Live counts like `1.2K` were parsed as `1.2`.
- Tweet dates were always `null`.
- A `403` or challenge page produced an empty success instead of a fallback.

## Verified

- 150 offline tests (`./run_tests.sh`).
- Live: user timelines over RSS, global search over the browser path, date-scoped
  user search, pagination to 40 results, instance fallback after a rate limit,
  and MCP calls from a host agent.
