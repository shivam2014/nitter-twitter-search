# API reference

## Python

### `nitter_search.search_tweets(...)`

```python
def search_tweets(
    user: Optional[str] = None,
    query: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 20,
    with_stats: bool = False,
    instance: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]
```

| Parameter | Type | Default | Meaning |
|-----------|------|---------|---------|
| `user` | str | `None` | Handle without `@`, 1-15 chars of `[A-Za-z0-9_]` |
| `query` | str | `None` | Search text; omit for the plain timeline |
| `since` | str | `None` | `YYYY-MM-DD`, inclusive |
| `until` | str | `None` | `YYYY-MM-DD` |
| `limit` | int | `20` | Max tweets; `0` returns immediately |
| `with_stats` | bool | `False` | Use a browser so counts are populated |
| `instance` | str | `None` | Pin one mirror instead of discovering |

Extra keyword arguments map to `SearchRequest`:

| Keyword | Default | Meaning |
|---------|---------|---------|
| `filters` | `[]` | Any of `media`, `links`, `quotes`, `replies`, `nativeretweets` |
| `min_faves` | `None` | Minimum likes |
| `min_retweets` | `None` | Minimum retweets |
| `min_replies` | `None` | Minimum replies |
| `include_replies` | `True` | Keep replies in timeline results |
| `allow_browser` | `True` | `False` forces RSS-only |
| `timeout` | `90` | Overall seconds across all instances |
| `instances` | `None` | List of mirrors to try, in order |

Returns `{"search_metadata": {...}, "tweets": [...]}`. See the README for the
field list.

### `nitter_search.SearchRequest`

The dataclass behind the helper, for callers who prefer to build one object:

```python
from nitter_search import SearchRequest, search

request = SearchRequest(user="NASA", limit=5, with_stats=True).validate()
result = search(request)
```

Raises nothing for bad input: validation failures come back in
`search_metadata.error` so a batch of calls never dies on one bad handle.

### Lower-level pieces

| Function | Purpose |
|----------|---------|
| `nitter_search.urls.build_search_url(...)` | Build a Nitter search URL |
| `nitter_search.urls.build_profile_url(...)` | Build a timeline URL |
| `nitter_search.parse.parse_html_timeline(html, instance)` | Parse rendered HTML |
| `nitter_search.parse.parse_rss_feed(xml, instance)` | Parse a Nitter feed |
| `nitter_search.parse.count_to_int("1.2K")` | `1200` |
| `nitter_search.instances.discover(force=False)` | Instance records, best first |
| `nitter_search.instances.check_all(limit=8)` | Live probe of mirrors |
| `nitter_search.transport.BrowserSession()` | Reusable browser for many fetches |

## CLI

```
nitter-search [--user HANDLE] [--query TEXT] [options]
```

| Flag | Meaning |
|------|---------|
| `--user, -u` | Scope to a handle |
| `--query, -q` | Search text |
| `--since`, `--until` | Date bounds, `YYYY-MM-DD` |
| `--filter` | Repeatable: `media`, `links`, `quotes`, `replies` |
| `--min-faves`, `--min-retweets`, `--min-replies` | Engagement floors |
| `--limit` | Max tweets (default 20) |
| `--stats` | Collect engagement counts via browser |
| `--no-browser` | RSS only |
| `--exclude-replies` | Drop replies |
| `--instance` | Pin a mirror, repeatable |
| `--timeout` | Overall seconds (default 90) |
| `--json` | JSON document (default) |
| `--ndjson` | One JSON tweet per line |
| `--text` | Tweet text only |
| `--pretty` | Indent JSON |
| `--check` | Probe instances and report health |
| `--list-instances` | Show the candidate list |
| `--refresh` | Ignore the cached instance list |
| `--quiet` | Suppress diagnostics on stderr |

Exit codes: `0` success, `1` transport failure, `2` protected or missing account,
`3` no results, `130` interrupted.

## MCP server

`nitter-search-mcp` speaks JSON-RPC 2.0 over stdio.

```json
{
  "mcp": {
    "servers": {
      "nitter": {"type": "local", "command": ["nitter-search-mcp"]}
    }
  }
}
```

Tools: `search_tweets`, `user_tweets`, `list_nitter_instances`. Responses carry
both `content[0].text` (JSON string) and `structuredContent` (object).
