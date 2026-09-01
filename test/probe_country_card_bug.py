# -*- coding: utf-8 -*-
"""Reproduce: a country card reported "0 suppliers" for a country that has 5.

Theory to test, not to assume: get_top_exporters with a `country` argument
overwrites the session's exporter list with a filtered one, so a card scoped to
a *different* country then counts zero rows in it.

    python test/probe_country_card_bug.py [base_url]
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

URL = (sys.argv[1].rstrip("/") if len(sys.argv) > 1
       else "https://taams-sourcing-desk.netlify.app")

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

CALL = """async ([n, a]) => {
  const mc = document.modelContext ?? navigator.modelContext;
  const t = (await mc.getTools()).find(x => x.name === n);
  const r = await mc.executeTool(t, JSON.stringify(a));
  return typeof r === 'string' ? r : JSON.stringify(r);
}"""

CARDS = """() => Array.from(document.querySelectorAll('#comparisonBoard .compare-card'))
  .map(c => c.innerText.replace(/\\n/g, ' | '))"""


def run(page, label, steps):
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1200)
    for name, args in steps:
        page.evaluate(CALL, [name, args])
    cards = page.evaluate(CARDS)
    print(f"\n{label}")
    for c in cards:
        mark = "  <-- 0 suppliers" if "0 supplier" in c else ""
        print(f"    {c}{mark}")


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False,
                          args=["--enable-features=WebMCP"])
    pg = b.new_page()
    pg.goto(f"{URL}/index.html", wait_until="networkidle")
    pg.wait_for_timeout(1500)

    # A: never pass `country` to get_top_exporters — the control.
    run(pg, "A. exporters fetched once, unfiltered", [
        ("get_import_price_trend", {"product_name": "망고"}),
        ("get_top_exporters", {"product_name": "망고"}),
        ("pin_to_comparison_board", {"product_name": "망고", "country": "Thailand"}),
        ("pin_to_comparison_board", {"product_name": "망고", "country": "Brazil"}),
    ])

    # B: what the agent actually did — narrow by country, then pin the other one.
    run(pg, "B. exporters re-fetched with country=Thailand, then Brazil pinned", [
        ("get_import_price_trend", {"product_name": "망고"}),
        ("get_top_exporters", {"product_name": "망고"}),
        ("pin_to_comparison_board", {"product_name": "망고", "country": "Thailand"}),
        ("get_top_exporters", {"product_name": "망고", "country": "Thailand"}),
        ("pin_to_comparison_board", {"product_name": "망고", "country": "Brazil"}),
    ])

    b.close()
