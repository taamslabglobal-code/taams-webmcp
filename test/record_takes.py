# -*- coding: utf-8 -*-
"""Record takes A and C of the demo video — the parts a person drives by hand.

Take B (the agent) is deliberately not here. Faking it would make the narration
false: it says "now in an agent-capable browser, so I can just ask", and that
has to actually be an agent.

Playwright's video does not draw a mouse pointer, and a screen recording with no
cursor does not read as a person operating anything. So a cursor is injected and
moved deliberately before each click — the movement is the point, not decoration.

    python test/record_takes.py [base_url]

Outputs WebM into shots/video/, then converts to mp4 if ffmpeg is present.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

URL = (sys.argv[1].rstrip("/") if len(sys.argv) > 1
       else "https://taams-sourcing-desk.netlify.app")
OUT = pathlib.Path(__file__).resolve().parent.parent / "shots" / "video"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

CURSOR_JS = """
() => {
  if (document.getElementById('__cur')) return;
  const c = document.createElement('div');
  c.id = '__cur';
  c.style.cssText = [
    'position:fixed', 'left:0', 'top:0', 'width:22px', 'height:22px',
    'z-index:2147483647', 'pointer-events:none', 'will-change:transform',
    'transition:transform .05s linear',
  ].join(';');
  c.innerHTML =
    '<svg viewBox="0 0 24 24" width="22" height="22">'
    + '<path d="M4 2 L4 18 L8.5 14 L11.5 21 L14.5 19.7 L11.6 13 L18 13 Z"'
    + ' fill="#111" stroke="#fff" stroke-width="1.4"/></svg>';
  document.body.appendChild(c);
  const ring = document.createElement('div');
  ring.id = '__curring';
  ring.style.cssText = [
    'position:fixed', 'left:0', 'top:0', 'width:34px', 'height:34px',
    'margin:-6px 0 0 -6px', 'border-radius:50%', 'z-index:2147483646',
    'pointer-events:none', 'background:rgba(29,78,216,.35)',
    'transform:scale(0)', 'transition:transform .18s ease-out',
  ].join(';');
  document.body.appendChild(ring);
  window.__moveCur = (x, y) => {
    c.style.transform = `translate(${x}px, ${y}px)`;
    ring.style.transform = `translate(${x}px, ${y}px) scale(0)`;
  };
  window.__clickPulse = (x, y) => {
    ring.style.transition = 'transform .18s ease-out';
    ring.style.transform = `translate(${x}px, ${y}px) scale(1)`;
    setTimeout(() => {
      ring.style.transition = 'transform .25s ease-in';
      ring.style.transform = `translate(${x}px, ${y}px) scale(0)`;
    }, 180);
  };
}
"""


class Take:
    """A page with a drawn cursor that moves before it clicks."""

    def __init__(self, page):
        self.page = page
        self.x, self.y = W // 2, H // 2
        page.evaluate(CURSOR_JS)
        page.evaluate("([x,y]) => window.__moveCur(x,y)", [self.x, self.y])

    def _ensure_cursor(self):
        self.page.evaluate(CURSOR_JS)

    def glide(self, x, y, steps=26):
        """Move in a straight line, easing out, so the eye can follow it."""
        self._ensure_cursor()
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            t = i / steps
            e = 1 - (1 - t) ** 3          # ease-out cubic
            cx, cy = x0 + (x - x0) * e, y0 + (y - y0) * e
            self.page.evaluate("([a,b]) => window.__moveCur(a,b)", [cx, cy])
            self.page.mouse.move(cx, cy)
            self.page.wait_for_timeout(14)
        self.x, self.y = x, y

    def click(self, selector, settle=700):
        el = self.page.locator(selector).first
        el.wait_for(state="visible", timeout=15000)
        box = el.bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        self.glide(cx, cy)
        self.page.wait_for_timeout(220)
        self.page.evaluate("([a,b]) => window.__clickPulse(a,b)", [cx, cy])
        el.click()
        self.page.wait_for_timeout(settle)

    def type_slowly(self, selector, text, per_char=170):
        self.click(selector, settle=200)
        for ch in text:
            self.page.keyboard.type(ch)
            self.page.wait_for_timeout(per_char)

    def hold(self, ms):
        self.page.wait_for_timeout(ms)


def new_page(browser, name):
    ctx = browser.new_context(
        viewport={"width": W, "height": H},
        record_video_dir=str(OUT),
        record_video_size={"width": W, "height": H},
    )
    page = ctx.new_page()
    page.goto(f"{URL}/index.html", wait_until="networkidle")
    page.wait_for_timeout(1600)
    return ctx, page


def finish(ctx, page, label):
    path = page.video.path()
    ctx.close()                      # video is only flushed on context close
    final = OUT / f"{label}.webm"
    if final.exists():
        final.unlink()
    pathlib.Path(path).rename(final)
    print(f"  saved {final.name}")
    return final


def main() -> int:
    made = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=False, args=["--enable-features=WebMCP"])

        # ── Take A — a person searches. No agent involved yet. ──────────────
        print("\nTake A — human search")
        ctx, page = new_page(browser, "takeA")
        t = Take(page)
        t.hold(1200)
        t.type_slowly("#searchInput", "mango")
        page.wait_for_selector("#searchResults li", timeout=15000)
        t.hold(1100)                                   # let the list be read
        t.click("#searchResults li", settle=3800)      # card + tables fill
        t.glide(250, 300)                              # drift to the price pill
        t.hold(2200)                                   # the $/kg beat
        made.append(finish(ctx, page, "takeA-human-search"))

        # ── Take C — the same actions, by hand, as buttons. ─────────────────
        print("\nTake C — human clicks the same buttons")
        ctx, page = new_page(browser, "takeC")
        t = Take(page)
        t.type_slowly("#searchInput", "mango", per_char=120)
        page.wait_for_selector("#searchResults li", timeout=15000)
        t.click("#searchResults li", settle=3600)
        t.hold(600)
        t.click("#pinBtn", settle=1300)
        chip = "#countryChips .chip[data-country]"
        page.wait_for_selector(chip, timeout=10000)
        # Second chip: the first is "All countries".
        t.click(f"{chip} >> nth=1", settle=1500)
        t.click("[data-action='draft-rfq'], #draftRfqBtn", settle=2200)
        t.hold(1800)
        made.append(finish(ctx, page, "takeC-human-clicks"))

        browser.close()

    if shutil.which("ffmpeg"):
        print("\nConverting to mp4")
        for src in made:
            dst = src.with_suffix(".mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-i", str(src), "-c:v", "libx264", "-preset", "slow",
                 "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", str(dst)],
                check=True)
            dur = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(dst)],
                capture_output=True, text=True).stdout.strip()
            print(f"  {dst.name}  {float(dur):.1f}s")

    print(f"\nOutput in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
