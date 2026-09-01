# -*- coding: utf-8 -*-
"""Environment probe — drives a real Chrome to check what WebMCP actually offers.

Everything here is checked against the running browser rather than against the
spec write-ups, because the two disagree. Checks:

  1. Does `modelContext` exist at all under --enable-features=WebMCP, and is it
     on `document` or on `navigator`? (Both are documented; only one is real.)
  2. Does registerTool() actually accept a tool?
  3. Is requestUserInteraction() present? The explainers describe it as the way
     to gate a sensitive action behind human approval. It is NOT in Chrome 151,
     which is why this project ships its own approval modal instead.
  4. Does the TAAMs API answer from page context? That path crosses both CORS
     and Cloudflare's bot filter, neither of which is visible in server code.

Usage:
    python -m http.server 8123 --bind 127.0.0.1   # separate shell, repo root
    python test/probe_webmcp_env.py

Exit code 0 if every check passes, 1 otherwise.
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8123/probe.html"

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    with sync_playwright() as p:
        # channel="chrome" uses the installed Chrome. Playwright's bundled
        # Chromium may predate WebMCP, and we want to measure the same browser
        # a judge would use, not a different one.
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,  # flag-gated experimental APIs can be absent headless
            args=["--enable-features=WebMCP"],
        )
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(3000)  # let the live API round-trip finish

        rows = page.eval_on_selector_all(
            "#out .row",
            "els => els.map(e => ({ ok: e.classList.contains('ok'),"
            " text: e.innerText.replace(/\\n/g, ' :: ') }))",
        )

        # Ask the browser directly too, independently of the page's own verdict.
        raw = page.evaluate(
            "() => { const m = document.modelContext ?? navigator.modelContext;"
            " return { where: document.modelContext ? 'document' :"
            " (navigator.modelContext ? 'navigator' : null),"
            " methods: m ? Object.getOwnPropertyNames(Object.getPrototypeOf(m)) : [] }; }"
        )

        browser.close()

    print("=" * 72)
    print("WebMCP environment probe (Playwright / Chrome / --enable-features=WebMCP)")
    print("=" * 72)
    failed = 0
    for r in rows:
        mark = "PASS" if r["ok"] else "FAIL"
        if not r["ok"]:
            failed += 1
        print(f"  [{mark}] {r['text']}")

    print()
    print(f"  modelContext lives on : {raw['where'] or 'nowhere'}")
    print(f"  methods exposed       : {', '.join(raw['methods']) or 'none'}")
    print()
    print(f"Result: {len(rows) - failed}/{len(rows)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
