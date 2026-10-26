# Filter reference

Nitter accepts Twitter's advanced-search parameters in the URL. This package
exposes the ones that work reliably across mirrors.

## Dates

```bash
nitter-search --user NASA --since 2026-10-01 --until 2026-10-26
```

- Format is `YYYY-MM-DD`, validated before any request is made.
- Both bounds are inclusive; `until` behaves like Twitter's — the day itself is
  mostly excluded. Widen by a day when precision matters.
- `since` after `until` is rejected with a clear error.

## Content filters

```bash
nitter-search --query "mars" --filter media
nitter-search --query "mars" --filter links --filter quotes
```

| Value | Meaning |
|-------|---------|
| `media` | Tweets with images, video or GIFs |
| `links` | Tweets containing URLs |
| `quotes` | Quote tweets |
| `replies` | Reply tweets |
| `nativeretweets` | Native retweets |

Repeat `--filter` to combine. Unknown values are rejected rather than silently
dropped, so a typo cannot quietly widen your search.

## Engagement floors

```bash
nitter-search --query "mars" --min-faves 100 --min-retweets 10 --min-replies 5
```

These are applied by the mirror, not by the client, so they reduce what has to be
transferred and parsed. Negative values are rejected.

## What the client does on top

- Results are de-duplicated by status id.
- Results are sorted newest-first by `date`, with undated tweets last.
- `--exclude-replies` drops reply items from timeline results.
- `limit` is applied after sorting, so you get the newest N, not the first N.

## What is not supported

- Full-text operators such as `from:`, `to:`, `filter:verified`, `lang:`.
  Mirrors differ in what they pass through, so behaviour would be unreliable.
- Media download. `media` contains URLs; fetching them is left to the caller.
