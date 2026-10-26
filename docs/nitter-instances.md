# Nitter instances

Public Nitter mirrors are unstable: they disappear, get rate limited, or start
serving an anti-bot challenge instead of content. Any hard-coded list is wrong
within a few months — that is why this package discovers instances at runtime.

## How discovery works

1. `https://status.d420.de/api/v1/instances` returns the mirrors the community
   health-checks, with a `healthy` flag, an `rss` capability flag and a
   reliability score.
2. The response is cached for six hours in
   `${XDG_CACHE_HOME:-~/.cache}/nitter-search/instances.json`.
3. Mirrors are filtered: unhealthy ones and known-dead domains are dropped.
4. `SEED_INSTANCES` from `nitter_search/instances.py` are appended as a fallback
   for when the status endpoint itself is unreachable.

When discovery fails entirely, the seed list keeps the tool working.

## How ordering works

Candidates are ordered by:

1. known-dead and bad hosts removed,
2. `healthy` first,
3. health memory: an instance that answered recently jumps ahead, one that
   failed in the last fifteen minutes sinks,
4. reliability points from the status endpoint.

Health memory lives in `.../nitter-search/health.json` and expires on its own.

## Per-instance behaviour that matters

| Response | Classified as | Effect |
|----------|---------------|--------|
| Nitter timeline HTML | `ok` | parse and return |
| Anubis / Gandalf / Cloudflare page | `challenge` | retry in a browser, then next instance |
| "Instance has no auth tokens, or is fully rate limited" | `ratelimited` | next instance |
| "Search has been disabled due to abuse" | `disabled` | next instance, timeline still usable |
| "User not found" / "No items found" | `missing` | stop, this is a real empty result |
| "This account's tweets are protected" | `protected` | stop, nothing to fetch |

## Inspecting the list yourself

```bash
nitter-search --list-instances         # cached candidates, in order
nitter-search --check                  # live probe of each candidate
nitter-search --check --instance https://nitter.netbub.com
```

`--check` fetches a known account's RSS feed per instance and reports latency,
whether RSS works, and whether the instance is challenge-gated.

## Pinning an instance

```bash
nitter-search --user NASA --instance https://nitter.netbub.com
nitter-search --user NASA --instance https://a.example --instance https://b.example
```

Pinning bypasses discovery order but not health memory; a pinned instance that
fails is reported in `search_metadata.instances_tried`.

## Note on nitter.net

`nitter.net` closed and now serves a static "this site is offline" page. It is
kept in `KNOWN_DEAD` so it is never tried, and `--check` will show `HTTP 410`
if you pin it deliberately.
