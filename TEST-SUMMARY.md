# Test summary

Last verified: 2026-10-26 (v2.0.0)

```
$ ./run_tests.sh
150 passed in 1.1s
```

| File | What it proves |
|------|----------------|
| `tests/test_urls.py` | URLs are built correctly, input is validated before any request |
| `tests/test_parse.py` | live-captured HTML and RSS parse into the documented shape |
| `tests/test_instances.py` | discovery, ordering, health memory, probe classification |
| `tests/test_search.py` | transport selection, instance fallback, dedupe, sorting |
| `tests/test_mcp.py` | MCP handshake, tool catalog, dispatch, crash containment |
| `tests/test_cli.py` | output modes, exit codes, flag-to-request mapping |

The suite is offline: HTTP payloads come from `tests/fixtures/` (captured from
real instances) and browser calls are faked. Nothing in `run_tests.sh` touches
the network.

## What the previous suite missed

The v1 suite reported "73 tests, 100% pass". Those tests did run, but every one
of them exercised the `camoufox not installed` error path: the browser was never
present in CI, so the scraper returned early every time. Nothing asserted that a
real page parsed, and three files hung for over 25 seconds each once camoufox was
actually installed. Two bugs hid behind that green result:

- `cli.py` imported `twitter_search.browser_scraper_camoufox`, a module that has
  never existed, so the CLI always took the ImportError branch.
- `browser_scraper.py` called `camoufox.Camoufox(...).start()`, which is not part
  of the API; `Camoufox` is a context manager whose `start` method does not exist.

The current suite asserts parsed content from real pages, which is why those bugs
cannot come back silently.

Run the network checks manually when you want live confirmation:

```bash
nitter-search --check
nitter-search --user NASA --limit 3 --no-browser
nitter-search --query "mars rover" --limit 3 --stats
```
