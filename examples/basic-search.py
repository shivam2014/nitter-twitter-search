#!/usr/bin/env python3
"""Fetch a user's recent tweets and print them."""

from nitter_search import search_tweets


def main() -> None:
    result = search_tweets(user="NASA", limit=5)
    metadata = result["search_metadata"]

    if metadata["error"]:
        print(f"error: {metadata['error']}")
        for attempt in metadata["instances_tried"]:
            print(f"  {attempt['url']}: {attempt['error'] or 'ok'}")
        return

    print(f"{metadata['total']} tweets via {metadata['mirror_used']} ({metadata['method']})\n")
    for tweet in result["tweets"]:
        print(f"[{tweet['date']}] {tweet['text'][:160]}")
        print(f"  {tweet['url']}\n")


if __name__ == "__main__":
    main()
