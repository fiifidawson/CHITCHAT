"""Google Scholar for discovery: paced, short queries, and stopped at the first block.

Scholar has no API and blocks automated callers. mmore's adapter uses `scholarly`, which
on a block opens a browser for a person to solve a captcha, or retries a 403 every one to
two minutes without end. Here each results page is one request, at least
SCHOLAR_INTERVAL_SECONDS after the last. The first block or error stops Scholar for the
rest of the run; the other sources keep going.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

SCHOLAR_INTERVAL_SECONDS = 10.0  # between results pages; Scholar publishes no limit
SCHOLAR_JITTER_SECONDS = 5.0
SCHOLAR_TIMEOUT_SECONDS = 30.0
SCHOLAR_MAX_QUERY_CHARS = 256  # Scholar ignores the rest of a longer query

_GROUP = re.compile(r"\(([^()]*)\)")


class ScholarBlocked(RuntimeError):
    """Scholar answered with a captcha, an error status, or not at all."""


class Pacer:
    """At least `interval` (plus random jitter) seconds between calls to `wait`."""

    def __init__(
        self,
        interval: float,
        jitter: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.interval = interval
        self.jitter = jitter
        self.clock = clock
        self.sleep = sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            delay = self._next - self.clock()
            if delay > 0:
                self.sleep(delay)
            self._next = self.clock() + self.interval + random.uniform(0, self.jitter)


class ScholarGate:
    """One run's Scholar requests: paced, and closed for good after the first failure."""

    def __init__(self, pacer: Pacer | None = None) -> None:
        self.pacer = pacer or Pacer(SCHOLAR_INTERVAL_SECONDS, SCHOLAR_JITTER_SECONDS)
        self.stopped: str | None = None

    def fetch(self, session: Any, url: str, has_captcha: Callable[[str], bool]) -> str:
        if self.stopped:
            raise ScholarBlocked(self.stopped)
        self.pacer.wait()
        try:
            response = session.get(url, timeout=SCHOLAR_TIMEOUT_SECONDS, follow_redirects=False)
        except Exception as e:
            raise self._block(f"no answer ({type(e).__name__})") from None
        if response.status_code in (301, 302, 303, 307):
            # Scholar sends blocked callers to a "Verifying..." page on google.com.
            raise self._block("a verification page")
        if response.status_code != 200:
            raise self._block(f"HTTP {response.status_code}")
        if has_captcha(response.text):
            raise self._block("a captcha")
        return response.text

    def _block(self, reason: str) -> ScholarBlocked:
        self.stopped = reason
        log.warning(
            "Google Scholar stopped answering (%s). No more Scholar searches this run; "
            "the other sources continue.",
            reason,
        )
        return ScholarBlocked(reason)


def scholar_query(boolean: str, limit: int = SCHOLAR_MAX_QUERY_CHARS) -> str:
    """Shorten `("a" OR "b") AND ("c" OR …)` to fit Scholar: fewer synonyms per concept.

    Keeps the first (most important) terms of every concept, as many as fit.
    """
    groups = [[t.strip() for t in g.split(" OR ") if t.strip()] for g in _GROUP.findall(boolean)]
    if not groups:
        return boolean[:limit]
    for n in range(max(len(g) for g in groups), 1, -1):
        query = " ".join("(" + " OR ".join(g[:n]) + ")" for g in groups)
        if len(query) <= limit:
            return query
    return " ".join(g[0] for g in groups)[:limit]


_gate = ScholarGate()


def paced_scholar_adapter() -> type:
    """mmore's Scholar adapter, with each page fetched through this run's gate."""
    from mmore.paper_discovery.sources.google_scholar import GoogleScholarAdapter

    class PacedScholarAdapter(GoogleScholarAdapter):
        def search(self, query: str, category_title: str) -> list[Any]:
            if _gate.stopped:
                return []
            try:
                from scholarly._navigator import Navigator
            except ImportError:
                return super().search(query, category_title)  # logs how to install it

            nav = Navigator()  # scholarly's shared instance

            def get_page(pagerequest: str, premium: bool = False) -> str:
                return _gate.fetch(nav._session1, pagerequest, nav._requests_has_captcha)

            nav._get_page = get_page
            try:
                return super().search(scholar_query(query), category_title)
            finally:
                del nav._get_page

    return PacedScholarAdapter


def use_paced_scholar(sources: list[str]) -> None:
    """Swap in the paced adapter for this run, if Scholar is a source."""
    global _gate
    if "google_scholar" not in sources:
        return
    from mmore.paper_discovery.sources import REGISTRY

    _gate = ScholarGate()
    REGISTRY["google_scholar"] = paced_scholar_adapter()
