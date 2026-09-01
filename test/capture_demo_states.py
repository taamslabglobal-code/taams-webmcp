# -*- coding: utf-8 -*-
"""Walk the demo flow and screenshot each state.

Used to write the video script against what the page actually renders rather
than against what it is supposed to render.

    python test/capture_demo_states.py [base_url]
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

URL = (sys.argv[1].rstrip("/") if len(sys.argv) > 1
       else "https://taams-sourcing-desk.netlify.app")
OUT = pathlib.Path(__file__).resolve().parent.parent / "shots"
OUT.mkdir(exist_ok=True)

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def agent(page, name, args):
    return page.evaluate(
        """async ([n, a]) => {
             const mc = document.modelContext ?? navigator.modelContext;
             const t = (await mc.getTools()).find(x => x.name === n);
             return await mc.executeTool(t, JSON.stringify(a));
           }""", [name, args])


def shot(page, label):
    path = OUT / f"{label}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  saved {path.name}")


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False,
                          args=["--enable-features=WebMCP"])
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(f"{URL}/index.html", wait_until="networkidle")
    pg.wait_for_timeout(1800)
    shot(pg, "1-landing")

    agent(pg, "search_import_products", {"query": "mango"})
    agent(pg, "get_import_price_trend", {"product_name": "망고"})
    agent(pg, "get_top_exporters", {"product_name": "망고"})
    agent(pg, "get_active_importers", {"product_name": "망고"})
    pg.wait_for_timeout(1200)
    shot(pg, "2-product-loaded")

    agent(pg, "pin_to_comparison_board", {"product_name": "망고"})
    agent(pg, "highlight_supplier_country", {"country": "Thailand"})
    pg.wait_for_timeout(900)
    shot(pg, "3-pinned-and-highlighted")

    pg.evaluate(
        """async () => {
             const mc = document.modelContext ?? navigator.modelContext;
             const t = (await mc.getTools()).find(x => x.name === 'draft_sourcing_request');
             window.__rfq = mc.executeTool(t, JSON.stringify({
               product_name: '망고', supplier_name: 'Thailand',
               quantity: '2 x 20ft containers, monthly',
               notes: 'FOB, Q4 2026 delivery, GAP certification required' }));
           }""")
    pg.wait_for_timeout(1500)
    shot(pg, "4-approval-modal")

    print(f"\nScreenshots in {OUT}")
    b.close()
