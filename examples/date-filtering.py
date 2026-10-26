#!/usr/bin/env python3
"""Search inside a date window, server-side."""

from nitter_search import search_tweets


def main() -> None:
    result = search_tweets(
        user="NASA",
        query="Artemis",
        since="2026-10-01",
        until="2026-10-26",
        limit=10,
    )

    for tweet in result["tweets"]:
        print(f"{tweet['date']}  {tweet['text'][:120]}")


if __name__ == "__main__":
    main()
