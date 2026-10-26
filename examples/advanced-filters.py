#!/usr/bin/env python3
"""Combine transport choice, filters and client-side ranking."""

from nitter_search import SearchRequest, search


def main() -> None:
    request = SearchRequest(
        query="mars rover",
        limit=20,
        with_stats=True,          # browser path: likes/replies/retweets populated
        filters=["media"],
        min_faves=50,
    )
    result = search(request)

    for tweet in result["tweets"]:
        likes = tweet["likes"] or 0
        print(f"{likes:>6} likes  @{tweet['author']}  {tweet['text'][:80]}")

    print(f"\nmethod: {result['search_metadata']['method']}")


if __name__ == "__main__":
    main()
