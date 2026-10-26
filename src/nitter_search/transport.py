"""Transport layer: cheap HTTP first, a real browser only when needed.

Most Nitter instances answer RSS over plain HTTP. A minority sit behind a
JavaScript proof-of-work gate (Anubis, "Gandalf", Cloudflare) that returns a
challenge page instead of content; those need an actual browser to solve the
challenge and redirect.

Browser backends, tried in order:

1. ``camoufox`` -- patched Firefox with a generated fingerprint, hardest to
   detect, optional dependency.
2. ``chromium`` -- Playwright's bundled Chromium.
3. ``chrome`` -- an already-installed Google Chrome via Playwright.

The last two exist so the tool still works when Camoufox's browser payload has
not been downloaded.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any, Optional, Tuple

from .parse import classify_page

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class TransportError(RuntimeError):
    """Network or browser failure that is worth retrying elsewhere."""


class ChallengeBlocked(TransportError):
    """The instance answered with an anti-bot challenge we could not clear."""


class BrowserUnavailable(TransportError):
    """No usable browser is installed."""


def http_get(url: str, timeout: float = 10.0) -> str:
    """Fetch ``url`` with a browser-like User-Agent and return the body."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429, 451):
            raise ChallengeBlocked(f"HTTP {exc.code} for {url}") from exc
        raise TransportError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise TransportError(f"{getattr(exc, 'reason', exc)} for {url}") from exc
    except OSError as exc:
        raise TransportError(f"{exc} for {url}") from exc


def camoufox_ready() -> bool:
    """True when Camoufox and its browser payload are both installed."""
    try:
        from camoufox import pkgman
    except ImportError:
        return False
    try:
        pkgman.installed_verstr()
    except Exception:
        return False
    return True


def _playwright_ready(firefox: bool = False) -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


class BrowserSession:
    """A reusable browser, started lazily and restarted on failure.

    Keeping one browser alive matters: launch costs roughly a second, while a
    page fetch after warm-up takes a few hundred milliseconds.
    """

    def __init__(
        self,
        headless: bool = True,
        block_images: bool = True,
        geoip: bool = False,
        challenge_timeout: float = 15.0,
        page_timeout: float = 25.0,
        max_pages: int = 60,
        backend: Optional[str] = None,
    ) -> None:
        self.headless = headless
        self.block_images = block_images
        self.geoip = geoip
        self.challenge_timeout = challenge_timeout
        self.page_timeout = page_timeout
        self.max_pages = max_pages
        self.preferred_backend = backend
        self.backend: Optional[str] = None
        self._camoufox: Any = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._pages_served = 0
        self.last_error: Optional[str] = None

    # -- lifecycle ---------------------------------------------------------
    @property
    def available(self) -> bool:
        return camoufox_ready() or _playwright_ready()

    def _start_camoufox(self) -> None:
        from camoufox.sync_api import Camoufox

        options: dict[str, Any] = {
            "headless": self.headless,
            "block_images": self.block_images,
            "humanize": False,
        }
        if self.geoip:
            options["geoip"] = True
        self._camoufox = Camoufox(**options)
        self._browser = self._camoufox.__enter__()
        self.backend = "camoufox"

    def _start_playwright(self, channel: Optional[str]) -> None:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        launch_options: dict[str, Any] = {"headless": self.headless}
        if channel:
            launch_options["channel"] = channel
        self._browser = self._playwright.chromium.launch(**launch_options)
        self.backend = channel or "chromium"

    def start(self) -> None:
        if self._browser is not None:
            return
        order = (
            [self.preferred_backend]
            if self.preferred_backend
            else ["camoufox", "chromium", "chrome"]
        )
        errors: list[str] = []
        for backend in order:
            try:
                if backend == "camoufox":
                    if not camoufox_ready():
                        errors.append("camoufox: browser payload not installed")
                        continue
                    self._start_camoufox()
                elif backend == "chromium":
                    if not _playwright_ready():
                        errors.append("chromium: playwright not installed")
                        continue
                    self._start_playwright(None)
                elif backend == "chrome":
                    if not _playwright_ready():
                        errors.append("chrome: playwright not installed")
                        continue
                    self._start_playwright("chrome")
                else:
                    errors.append(f"{backend}: unknown backend")
                    continue
                self._context = self._browser.new_context()
                self._pages_served = 0
                return
            except Exception as exc:
                errors.append(f"{backend}: {exc}")
                self.close()
        raise BrowserUnavailable(
            "No usable browser. Install one with `camoufox fetch`, "
            "`playwright install chromium`, or install Google Chrome. Tried -- "
            + "; ".join(errors)
        )

    def close(self) -> None:
        self._recycle()
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._camoufox is not None:
            try:
                self._camoufox.__exit__(None, None, None)
            except Exception:
                pass
            self._camoufox = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __enter__(self) -> "BrowserSession":
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # -- page handling -----------------------------------------------------
    def _new_page(self):
        """Return the reusable page, creating the context on first use.

        Cookies and localStorage must survive between fetches: solving an
        instance's proof-of-work is the expensive part, and it is remembered in
        the context. Reusing one page also avoids a fresh context per request.
        """
        if self._page is not None:
            try:
                if not self._page.is_closed():
                    return self._page
            except Exception:
                pass
            self._page = None
        if self._context is None or self._pages_served >= self.max_pages:
            self._recycle()
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.page_timeout * 1000)
        if self.block_images:
            try:
                self._page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
            except Exception:
                pass
        self._pages_served += 1
        return self._page

    def _recycle(self) -> None:
        """Drop the page and context, keeping the browser process."""
        if self._page is not None:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        self._pages_served = 0

    def _await_content(self, page, timeout: float) -> str:
        """Wait for a challenge to clear, then report what arrived."""
        deadline = time.monotonic() + timeout
        started = time.monotonic()
        saw_challenge = False
        while time.monotonic() < deadline:
            try:
                title = page.title() or ""
            except Exception as exc:
                self.last_error = str(exc)
                title = ""
            if classify_page(title) == "challenge":
                saw_challenge = True
                page.wait_for_timeout(400)
                continue
            try:
                has_timeline = page.query_selector(".timeline-item") is not None
                has_notice = (
                    page.query_selector(".error-panel") is not None
                    or page.query_selector(".timeline") is not None
                    or page.query_selector(".profile-card") is not None
                )
            except Exception as exc:
                self.last_error = str(exc)
                page.wait_for_timeout(250)
                continue
            if has_timeline or has_notice:
                body = page.content()
                if classify_page(body) == "challenge":
                    saw_challenge = True
                    page.wait_for_timeout(400)
                    continue
                return body

            # Pages that are neither a timeline nor a Nitter notice (a bare
            # "search has been disabled" text response, for example) must be
            # returned rather than waited on until the timeout.
            settled = time.monotonic() - started > 1.5
            if settled:
                try:
                    loaded = page.evaluate("() => document.readyState") == "complete"
                    has_text = page.evaluate(
                        "() => document.body ? document.body.innerText.trim().length : 0"
                    )
                except Exception:
                    loaded, has_text = False, 0
                if loaded and has_text:
                    body = page.content()
                    if classify_page(body) != "challenge":
                        return body
                    saw_challenge = True
            page.wait_for_timeout(250)

        body = ""
        try:
            body = page.content()
        except Exception:
            pass
        if saw_challenge or classify_page(body) == "challenge":
            raise ChallengeBlocked("Anti-bot challenge did not clear")
        if body:
            return body
        raise TransportError("Timed out waiting for page content")

    def fetch(self, url: str, timeout: Optional[float] = None) -> str:
        """Load ``url`` in the browser and return the rendered HTML."""
        self.start()
        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.page_timeout * 1000)
        except Exception as exc:
            self.last_error = str(exc)
            raise TransportError(f"Navigation failed for {url}: {exc}") from exc
        return self._await_content(page, timeout or self.challenge_timeout)


_default_session: Optional[BrowserSession] = None


def get_default_session(**kwargs: Any) -> BrowserSession:
    """Return the process-wide browser session, creating it on first use."""
    global _default_session
    if _default_session is None:
        _default_session = BrowserSession(**kwargs)
    return _default_session


def shutdown_default_session() -> None:
    global _default_session
    if _default_session is not None:
        _default_session.close()
        _default_session = None
