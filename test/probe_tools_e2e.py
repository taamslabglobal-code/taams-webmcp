# -*- coding: utf-8 -*-
"""End-to-end check of all seven WebMCP tools, driven through a real Chrome.

No ChatGPT needed: WebMCP exposes getTools()/executeTool() to the page, so a
test can invoke the tools exactly the way an agent would.

What this proves, and why each claim needs proving:

  1. All seven tools really register. Asked of the browser, not of our own code —
     a page can call registerTool() and still end up with nothing registered.
  2. The four lookup tools return real data from the live TAAMs API.
  3. The two screen-control tools change the page and make ZERO network
     requests. The README invites a judge to open the network tab and check
     this, so it had better be true. (It was not, at first: the pin tool used to
     resolve names over the network. That is what this assertion caught.)
  4. The action tool sends nothing without human approval — the one claim where
     being wrong would matter to a real supplier.

Usage:
    python -m http.server 8123 --bind 127.0.0.1   # separate shell, repo root
    python test/probe_tools_e2e.py

    # or against a deployed origin, which is the run that actually counts —
    # HTTPS, a real hostname, and a CDN in front all differ from localhost:
    python test/probe_tools_e2e.py https://example.netlify.app

Exit code 0 if every check passes, 1 otherwise.
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

DEFAULT_URL = "http://127.0.0.1:8123/index.html"
URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else DEFAULT_URL
if not URL.endswith(".html"):
    URL += "/index.html"
EXPECTED = {
    "search_import_products", "get_import_price_trend", "get_top_exporters",
    "get_active_importers", "pin_to_comparison_board",
    "highlight_supplier_country", "draft_sourcing_request",
}

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, f"{label}{'  :: ' + detail if detail else ''}"))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"\n         {detail}" if detail else ""))


def call(page, name, args):
    """Invoke a tool the way an agent does.

    The real convention, established by asking the browser (probe_api_shape.py):
        executeTool(<tool object from getTools()>, <arguments as JSON string>)
    A name string or a plain arguments object is rejected.
    """
    return page.evaluate(
        """async ([n, a]) => {
             const mc = document.modelContext ?? navigator.modelContext;
             const tool = (await mc.getTools()).find(t => t.name === n);
             if (!tool) return { ok: false, text: `tool not registered: ${n}` };
             try {
               const r = await mc.executeTool(tool, JSON.stringify(a));
               const text = typeof r === 'string' ? r : JSON.stringify(r);
               return { ok: true, text: text.slice(0, 400) };
             } catch (e) { return { ok: false, text: String(e) }; }
           }""",
        [name, args],
    )


def check_module_versions() -> None:
    """Every import of a module must carry the same ?v= token.

    The browser keys modules by URL, so './ui.js?v=2' and './ui.js?v=1' are two
    separate instances with separate state — the agent would drive one UI object
    while the person looks at another. Nothing at runtime announces this; the
    page just quietly stops agreeing with itself. Cheap to check statically.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    found: dict[str, set[str]] = {}
    for rel in ("index.html", "src/tools.js"):
        text = (root / rel).read_text(encoding="utf-8")
        for spec in re.findall(r"from\s+'(\./[^']+\.js)(\?v=\d+)?'", text):
            path, ver = spec[0].rsplit("/", 1)[-1], spec[1]
            found.setdefault(path, set()).add(ver or "(none)")

    bad = {k: v for k, v in found.items() if len(v) > 1}
    check(not bad, f"module ?v= tokens agree across {len(found)} imported files",
          f"mismatched: {bad}" if bad else
          " ".join(f"{k}{list(v)[0]}" for k, v in sorted(found.items())))


def main() -> int:
    print("\n" + "=" * 70)
    print("0. Static: module cache-busting tokens")
    print("=" * 70)
    check_module_versions()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=False, args=["--enable-features=WebMCP"])
        page = browser.new_page()

        api_calls: list[str] = []
        page.on("request", lambda r: api_calls.append(r.url)
                if "/api/v1/" in r.url else None)

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(1500)

        print(f"\nTarget: {URL}")
        print("\n" + "=" * 70)
        print("1. Registration")
        print("=" * 70)
        names = page.evaluate(
            "async () => { const mc = document.modelContext ?? navigator.modelContext;"
            " const t = await mc.getTools(); return t.map(x => x.name); }")
        check(set(names) == EXPECTED, f"{len(names)} tools registered in the browser",
              f"missing {sorted(EXPECTED - set(names))} / extra {sorted(set(names) - EXPECTED)}"
              if set(names) != EXPECTED else ", ".join(sorted(names)))

        print("\n" + "=" * 70)
        print("2. Tier A - lookup (live data)")
        print("=" * 70)
        r = call(page, "search_import_products", {"query": "mango"})
        check(r["ok"] and "망고" in r["text"], "search_import_products('mango')", r["text"][:150])

        r = call(page, "get_import_price_trend", {"product_name": "망고", "month": 6})
        check(r["ok"] and "3.48" in r["text"], "get_import_price_trend(mango, June)", r["text"][:150])

        # Omitting the month is the common case — an agent that was not told a
        # month will not invent one. It used to send 0, which the endpoint turns
        # into the date "YYYY-00-01" and answers with a 500. Pinning an explicit
        # month in every test is exactly how that shipped unnoticed.
        r = call(page, "get_import_price_trend", {"product_name": "망고"})
        check(r["ok"] and "/kg" in r["text"] and "500" not in r["text"],
              "get_import_price_trend(mango) with no month", r["text"][:150])

        r = call(page, "get_top_exporters", {"product_name": "망고"})
        check(r["ok"] and "태국" in r["text"], "get_top_exporters(mango)", r["text"][:150])

        r = call(page, "get_active_importers", {"product_name": "망고"})
        check(r["ok"], "get_active_importers(mango)", r["text"][:150])

        print("\n" + "=" * 70)
        print("3. Tier B - screen control (must make zero network requests)")
        print("=" * 70)
        before = len(api_calls)

        r = call(page, "pin_to_comparison_board", {"product_name": "망고"})
        pinned = page.locator('#comparisonBoard [data-action="focus-pinned"]').count()
        check(r["ok"], "pin_to_comparison_board(mango)", r["text"][:150])
        check(pinned > 0, f"a card actually appeared on the comparison board (count={pinned})")

        r = call(page, "highlight_supplier_country", {"country": "베트남"})
        check(r["ok"], "highlight_supplier_country(Vietnam)", r["text"][:150])

        # The demo's actual question is "Thai mango or Brazilian?" — same
        # product, two origins. A board keyed on product alone cannot hold that
        # question, so this is the assertion that the centrepiece works at all.
        call(page, "pin_to_comparison_board", {"product_name": "망고", "country": "Thailand"})
        call(page, "pin_to_comparison_board", {"product_name": "망고", "country": "Brazil"})
        cards = page.evaluate(
            """() => Array.from(document.querySelectorAll(
                 '#comparisonBoard [data-action=\\"focus-pinned\\"]'))
                 .map(c => c.innerText.replace(/\\n/g, ' | '))""")
        check(len(cards) >= 2, f"two origins of one product pin as separate cards ({len(cards)})",
              " // ".join(cards[:3]))

        prices = page.evaluate(
            """() => Array.from(document.querySelectorAll(
                 '#comparisonBoard .compare-price')).map(e => e.innerText.trim())""")
        check(len(set(prices)) > 1, "each origin card shows its own price, not one repeated figure",
              " / ".join(prices))

        after = len(api_calls)
        check(after == before, "Tier B made zero network requests",
              f"{after - before} request(s) fired" if after != before else "0 confirmed")

        # Below here is a Tier A call, so it must come after the count above —
        # putting it inside the window made the zero-fetch check fail on the
        # test's own traffic and blame the product for it.
        #
        # Narrowing the fetch to one country used to overwrite the session list,
        # so a card for any other country counted zero suppliers in it. Run the
        # sequence that broke it and check the cards still hold real counts.
        call(page, "get_top_exporters", {"product_name": "망고", "country": "Thailand"})
        counts = page.evaluate(
            """() => Array.from(document.querySelectorAll(
                 '#comparisonBoard .compare-suppliers')).map(e => e.innerText.trim())""")
        zero = [c for c in counts if c.startswith("0 supplier")]
        check(not zero, "country cards survive a narrowed re-fetch without dropping to zero",
              " / ".join(counts))

        print("\n" + "=" * 70)
        print("4. Tier C - nothing leaves the page without approval")
        print("=" * 70)
        opened: list[str] = []
        page.on("popup", lambda pop: opened.append(pop.url))

        page.evaluate(
            """async () => {
                 const mc = document.modelContext ?? navigator.modelContext;
                 const tool = (await mc.getTools()).find(t => t.name === 'draft_sourcing_request');
                 window.__rfq = mc.executeTool(tool, JSON.stringify({
                   product_name: '망고', quantity: '2 x 20ft containers',
                   supplier_name: 'Thailand', notes: 'FOB, Q4 delivery' }));
               }""")
        page.wait_for_timeout(1500)

        # An earlier version of this asked for 'dialog[open], .modal:not(.hidden)'
        # and passed even when every executeTool call had failed. Look at the one
        # element that actually matters instead.
        modal_visible = page.evaluate(
            """() => { const m = document.getElementById('rfqModal');
                 return !!m && !m.classList.contains('hidden'); }""")
        check(modal_visible, "the approval modal opened (the tool stopped instead of sending)")
        check(not opened, "nothing opened before approval",
              f"opened: {opened}" if opened else "no mail client launched")

        # Decline it, and confirm declining really does mean nothing happens.
        for sel in ("text=Cancel", "[data-action=rfqCancel]", "#rfqCancel"):
            try:
                page.locator(sel).first.click(timeout=1500)
                break
            except Exception:
                continue
        page.wait_for_timeout(800)
        res = page.evaluate("async () => { try { return JSON.stringify(await window.__rfq); }"
                            " catch (e) { return String(e); } }")
        check("cancel" in res.lower(), "the cancellation is reflected in the tool result", res[:200])
        check(not opened, "still no mail client after cancelling")

        print("\n" + "=" * 70)
        print("5. The human path - typing and clicking, no agent involved")
        print("=" * 70)
        # The whole premise is that a person and an agent drive the same page.
        # Testing only executeTool checks half of that, and the half that broke
        # first was this one: search worked, clicking a result 500'd.
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1200)

        page.fill("#searchInput", "mango")
        page.wait_for_selector("#searchResults li", timeout=15000)
        first = page.locator("#searchResults li").first.inner_text()
        check(True, "autocomplete returned suggestions", first.replace("\n", " / ")[:100])

        page.locator("#searchResults li").first.click()
        page.wait_for_timeout(6000)

        log = page.inner_text("#activityLog") if page.locator("#activityLog").count() else ""
        check("Could not load" not in log and "500" not in log,
              "clicking a suggestion loads the product without an error",
              log.replace("\n", " | ")[-200:] or "(activity log empty)")

        rendered = page.evaluate(
            """() => { const t = document.body.innerText;
                 return { hasPrice: /\\$\\d+\\.\\d{2}/.test(t),
                          hasSupplier: /clearances|suppliers|Thailand|태국/i.test(t),
                          unknown: (t.match(/Unknown supplier/g) || []).length }; }""")
        check(rendered["hasPrice"], "a unit price is actually on screen after the click")
        check(rendered["hasSupplier"], "supplier data is actually on screen after the click")

        # Named suppliers are the whole point; a table of "Unknown supplier"
        # renders without error and looks fine to any assertion that only asks
        # whether something appeared.
        check(rendered["unknown"] == 0, "suppliers are named, not 'Unknown supplier'",
              f"{rendered['unknown']} unnamed rows on screen" if rendered["unknown"] else "0 unnamed")

        browser.close()

    failed = sum(1 for ok, _ in results if not ok)
    print("\n" + "=" * 70)
    print(f"Result: {len(results) - failed}/{len(results)} passed")
    if failed:
        print("\nFailures:")
        for ok, label in results:
            if not ok:
                print(f"  - {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
