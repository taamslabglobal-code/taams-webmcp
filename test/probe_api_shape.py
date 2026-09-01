# -*- coding: utf-8 -*-
"""Ask the browser what document.modelContext's calling convention actually is.

Calling executeTool(name, argsObject) — the obvious reading of the docs — fails
with "The provided value is not of type 'RegisteredTool'". Rather than guess
again, this probe enumerates the object and then tries each plausible convention
against the live implementation until one returns a real result.

Answer, for the record (Chrome 151):
    executeTool(<tool object from getTools()>, <arguments as a JSON string>)
A name string is rejected, and so is a plain object of arguments.

Usage:
    python -m http.server 8123 --bind 127.0.0.1   # separate shell, repo root
    python test/probe_api_shape.py
"""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=False,
                          args=["--enable-features=WebMCP"])
    pg = b.new_page()
    pg.goto("http://127.0.0.1:8123/index.html", wait_until="networkidle")
    pg.wait_for_timeout(1500)

    info = pg.evaluate("""async () => {
        const mc = document.modelContext ?? navigator.modelContext;
        const tools = await mc.getTools();
        const t0 = tools[0];
        const out = {
          count: tools.length,
          names: tools.map(t => t.name),
          firstType: Object.prototype.toString.call(t0),
          firstCtor: t0 && t0.constructor && t0.constructor.name,
          firstOwnKeys: t0 ? Object.keys(t0) : [],
          firstProtoKeys: t0 ? Object.getOwnPropertyNames(Object.getPrototypeOf(t0)) : [],
          executeToolLength: mc.executeTool.length,
        };
        // Try each candidate convention against the real implementation.
        const attempts = {};
        const args = { query: 'mango' };
        const byName = tools.find(t => t.name === 'search_import_products');
        for (const [label, fn] of Object.entries({
          'executeTool(tool, args)': () => mc.executeTool(byName, args),
          'executeTool(tool, JSON.stringify(args))': () => mc.executeTool(byName, JSON.stringify(args)),
          'executeTool(name, JSON.stringify(args))': () => mc.executeTool('search_import_products', JSON.stringify(args)),
          'executeTool(tool, {input:args})': () => mc.executeTool(byName, { input: args }),
          'executeTool(tool, {arguments:JSON.stringify(args)})': () => mc.executeTool(byName, { arguments: JSON.stringify(args) }),
        })) {
          try {
            const r = await fn();
            attempts[label] = 'OK :: ' + JSON.stringify(r).slice(0, 160);
          } catch (e) { attempts[label] = 'ERR :: ' + String(e).slice(0, 160); }
        }
        out.attempts = attempts;
        return out;
      }""")
    b.close()

print(json.dumps(info, ensure_ascii=False, indent=2))
