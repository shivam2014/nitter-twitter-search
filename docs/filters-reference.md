# Search Filters Reference

This document describes all available search filters for the twitter-search skill.

## Filter Types

All filters can be used in two modes: **include** or **exclude**.

### Include Filters

These filters **add** tweets matching the criteria to the results.

| Filter | Description |
|--------|-------------|
| `retweets` | Include retweets in results |
| `media` | Include tweets with any media (images/videos) |
| `videos` | Include video tweets |
| `news` | Include news tweets (from Twitter's news section) |
| `native_videos` | Include tweets with native Twitter videos |
| `replies` | Include reply tweets |
| `links` | Include tweets with external links |
| `images` | Include image tweets |
| `quotes` | Include quote tweets |
| `spaces` | Include Twitter Spaces tweets |

### Exclude Filters

These filters **remove** tweets matching the criteria from the results.

| Filter | Description |
|--------|-------------|
| `exclude-retweets` | Remove retweets from results |
| `exclude-media` | Remove tweets with any media |
| `exclude-videos` | Remove video tweets |
| `exclude-news` | Remove news tweets |
| `exclude-native-videos` | Remove native video tweets |
| `exclude-replies` | Remove reply tweets |
| `exclude-links` | Remove tweets with external links |
| `exclude-images` | Remove image tweets |
| `exclude-quotes` | Remove quote tweets |
| `exclude-spaces` | Remove Spaces tweets |

## Usage Examples

### Example 1: Get Only Original Tweets with Images
```bash
hermes twitter-search --query "python" \
  --exclude-retweets \
  --exclude-replies \
  --include-images
```

### Example 2: Find Viral Content (High Engagement)
```bash
hermes twitter-search --query "ai" \
  --include-images \
  --include-videos \
  --min-likes 1000
```

### Example 3: Exclude Promotional Content
```bash
hermes twitter-search --query "crypto" \
  --exclude-retweets \
  --exclude-replies \
  --exclude-links
```

### Example 4: Find Video Content Only
```bash
hermes twitter-search --user "ycombinator" --query "" \
  --include-videos \
  --include-native-videos
```

## Date Range Filtering

Use these filters to limit results to a specific time period:

```bash
--start-date YYYY-MM-DD  # Start date (inclusive)
--end-date YYYY-MM-DD    # End date (inclusive)
```

### Example: Q1 2024 Bitcoin Tweets
```bash
hermes twitter-search --query "bitcoin" \
  --start-date 2024-01-01 \
  --end-date 2024-03-31
```

## Minimum Likes Filter

```bash
--min-likes INTEGER  # Only get tweets with X or more likes
```

### Example: Only Highly-Liked Tweets
```bash
hermes twitter-search --query "machine learning" \
  --min-likes 500
```

## Combining Filters

You can combine multiple filters:

```bash
hermes twitter-search --query "tesla" \
  --include-videos \
  --include-images \
  --exclude-retweets \
  --exclude-replies \
  --min-likes 100 \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

This will find:
- Tweets containing "tesla"
- With videos OR images
- But NOT retweets or replies
- With at least 100 likes
- Between Jan 1, 2024 and Dec 31, 2024

## Filter Notes

1. **Filters are applied by Nitter**, not by the client. Not all filters may be available on all mirror instances.

2. **Conflicting filters:** Using both `--include-retweets` and `--exclude-retweets` will result in the exclude filter taking precedence (retweets will be excluded).

3. **Date range:** If only `--start-date` is provided, no end date limit is applied. Same for `--end-date`.

4. **Minimum likes:** Setting `--min-likes 0` is equivalent to not using the filter.

5. **Filter combinations:** Some filter combinations may return no results. For example, `--exclude-images --exclude-videos --exclude-media` might filter out most visual content.

## Filter Mapping to Nitter API

The filters are translated to Nitter's URL parameters:

| CLI Flag | Nitter Parameter |
|----------|------------------|
| `--include-retweets` | `retweets=1` |
| `--exclude-retweets` | `retweets_excl=1` |
| `--include-media` | `media=1` |
| `--include-videos` | `videos=1` |
| `--start-date 2024-01-01` | `since=2024-01-01` |
| `--end-date 2024-12-31` | `until=2024-12-31` |
| `--min-likes 100` | `min_likes=100` |

## Troubleshooting

**"Filter not recognized"**
- Check the filter name spelling
- Use `--help` to see all available filters

**"No results found"**
- Try removing some filters to broaden the search
- Check if the date range is correct
- Lower the `--min-likes` threshold

**"Mirror doesn't support this filter"**
- Try a different mirror instance
- Some filters may not be available on all Nitter instances
