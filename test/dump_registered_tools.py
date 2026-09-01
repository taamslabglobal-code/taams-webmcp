# -*- coding: utf-8 -*-
"""Dump the tool definitions exactly as the browser hands them to an agent.

Used to rehearse tool *selection*: an agent sees only these names, descriptions
and schemas, so that is all a selection test should be given. Reading the
descriptions out of the source would test a different thing.

    python test/dump_registered_tools.py [base_url] > tools.json
"""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

URL = (sys.argv[1].rstrip("/") if len(sys.argv) > 1
       else "https://taams-sourcing-desk.netlify.app")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False,
                          args=["--enable-features=WebMCP"])
    pg = b.new_page()
    pg.goto(f"{URL}/index.html", wait_until="networkidle")
    pg.wait_for_timeout(1500)
    tools = pg.evaluate(
        """async () => {
             const mc = document.modelContext ?? navigator.modelContext;
             return (await mc.getTools()).map(t => ({
               name: t.name, description: t.description, inputSchema: t.inputSchema,
             }));
           }""")
    b.close()

sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(tools, ensure_ascii=False, indent=2))
