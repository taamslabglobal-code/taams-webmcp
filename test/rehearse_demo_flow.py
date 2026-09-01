# -*- coding: utf-8 -*-
"""Mechanical rehearsal — run the demo sequence N times and look for flakiness.

WHAT THIS MEASURES: whether the intended call chain works reliably, back to
back, with the timing a live demo will have. Race conditions, state left over
between calls, slow API responses.

WHAT THIS DOES NOT MEASURE: whether a real agent *chooses* this sequence from
the user's question. That is the LLM's decision and executeTool bypasses it
entirely. Tool-choice is rehearsed separately; a live run in the actual agent
browser is still required before recording.

    python test/rehearse_demo_flow.py [base_url] [runs]
"""
from __future__ import annotations

import json
import statistics
import sys
import time

from playwright.sync_api import sync_playwright

URL = (sys.argv[1].rstrip("/") if len(sys.argv) > 1
       else "https://taams-sourcing-desk.netlify.app")
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 5

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# The sequence the script asks the agent to perform, in order.
SEQUENCE = [
    ("search_import_products", {"query": "mango"}),
    ("get_import_price_trend", {"product_name": "망고"}),
    ("get_top_exporters", {"product_name": "망고"}),
    ("get_active_importers", {"product_name": "망고"}),
    ("pin_to_comparison_board", {"product_name": "망고"}),
    ("highlight_supplier_country", {"country": "Thailand"}),
]

CALL_JS = """async ([n, a]) => {
  const mc = document.modelContext ?? navigator.modelContext;
  const tool = (await mc.getTools()).find(t => t.name === n);
  if (!tool) return { ok: false, text: 'not registered: ' + n };
  try {
    const r = await mc.executeTool(tool, JSON.stringify(a));
    const text = typeof r === 'string' ? r : JSON.stringify(r);
    return { ok: !/\"isError\":true/.test(text), text: text.slice(0, 300) };
  } catch (e) { return { ok: false, text: String(e) }; }
}"""


def main() -> int:
    timings: dict[str, list[float]] = {n: [] for n, _ in SEQUENCE}
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=False, args=["--enable-features=WebMCP"])

        for run in range(1, RUNS + 1):
            page = browser.new_page()   # fresh context each run, like a fresh viewer
            page.goto(f"{URL}/index.html", wait_until="networkidle")
            page.wait_for_timeout(1200)

            print(f"\nRun {run}/{RUNS}")
            for name, args in SEQUENCE:
                t0 = time.time()
                r = page.evaluate(CALL_JS, [name, args])
                dt = time.time() - t0
                timings[name].append(dt)
                mark = "ok " if r["ok"] else "FAIL"
                print(f"  [{mark}] {name:28} {dt:5.2f}s")
                if not r["ok"]:
                    failures.append(f"run {run} · {name} · {r['text'][:160]}")

            # Did the screen actually end up in the state the script describes?
            state = page.evaluate(
                """() => ({
                     pinned: document.querySelectorAll(
                       '#comparisonBoard [data-action=\\"focus-pinned\\"]').length,
                     // The class is row-dim. Guessing 'is-dimmed' here reported
                     // five clean runs as five failures — a test that is wrong
                     // in the pessimistic direction still wastes the same time.
                     dimmed: document.querySelectorAll('tr.row-dim').length,
                     highlighted: document.querySelectorAll('tr.row-highlight').length,
                     unknown: (document.body.innerText.match(/Unknown supplier/g) || []).length,
                   })""")
            ok_state = state["pinned"] >= 1 and state["dimmed"] >= 1 and state["unknown"] == 0
            print(f"  [{'ok ' if ok_state else 'FAIL'}] end state "
                  f"pinned={state['pinned']} dimmed={state['dimmed']} "
                  f"highlighted={state['highlighted']} unnamed={state['unknown']}")
            if not ok_state:
                failures.append(f"run {run} · end state {json.dumps(state)}")
            page.close()

        browser.close()

    print("\n" + "=" * 68)
    print(f"{RUNS} runs · timing per call (median / max)")
    print("=" * 68)
    total = 0.0
    for name, _ in SEQUENCE:
        ts = timings[name]
        med, mx = statistics.median(ts), max(ts)
        total += med
        flag = "  <-- slow on camera" if mx > 4 else ""
        print(f"  {name:28} {med:5.2f}s / {mx:5.2f}s{flag}")
    print(f"\n  intended chain, median total: {total:.1f}s "
          f"(script budgets 26s for this stretch)")

    print(f"\n  failures: {len(failures)}")
    for f in failures:
        print(f"    - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
