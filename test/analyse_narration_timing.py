# -*- coding: utf-8 -*-
"""Narration timing analysis — where the 3-minute budget is actually going.

The contest caps the demo video at 3:00. A narration that runs over is not a
style problem, it is a disqualification risk, so this measures rather than
guesses: total speech, total silence, and which gaps are paragraph breaks.

    python test/analyse_narration_timing.py <audio file>
"""
from __future__ import annotations

import re
import subprocess
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

if len(sys.argv) < 2:
    sys.exit(__doc__.strip().splitlines()[-1].strip())
AUDIO = sys.argv[1]
LIMIT = 180.0          # contest hard limit, seconds
TARGET = 175.0         # leave a margin; encoders round up

# Script sections, in order, with the seconds the shooting script budgets.
SECTIONS = [
    ("1  black screen — two questions", 13),
    ("2  black screen — by hand today", 13),
    ("3  human types, page fills", 22),
    ("4  agent badge, the question", 12),
    ("5  agent works, page changes", 26),
    ("6  Tier B — pin + highlight", 26),
    ("7  approval modal — Approve", 34),
    ("8  human clicks the same buttons", 16),
    ("9  closing", 13),
]


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def silences(path: str, thresh_db: int = -32, min_dur: float = 0.30):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", f"silencedetect=noise={thresh_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True)
    spans, start = [], None
    for line in out.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", line)
        if m and start is not None:
            spans.append((start, float(m.group(1)), float(m.group(2))))
            start = None
    return spans


total = probe_duration(AUDIO)
gaps = silences(AUDIO)
silence_total = sum(d for _, _, d in gaps)
speech = total - silence_total

print("=" * 68)
print(f"Narration: {AUDIO}")
print("=" * 68)
print(f"  total     {total:6.1f}s   ({int(total // 60)}:{total % 60:04.1f})")
print(f"  speech    {speech:6.1f}s")
print(f"  silence   {silence_total:6.1f}s   in {len(gaps)} gaps")
print(f"  limit     {LIMIT:6.1f}s   -> over by {total - LIMIT:.1f}s"
      if total > LIMIT else f"  limit     {LIMIT:6.1f}s   -> {LIMIT - total:.1f}s to spare")

# How much comes back by capping every pause?
print("\nTrimming pauses alone:")
for cap in (0.60, 0.45, 0.35, 0.25):
    saved = sum(max(0.0, d - cap) for _, _, d in gaps)
    after = total - saved
    verdict = "fits" if after <= TARGET else f"still {after - LIMIT:+.0f}s vs limit"
    print(f"  cap every gap at {cap:.2f}s -> saves {saved:5.1f}s, total {after:6.1f}s   {verdict}")

# Paragraph breaks: the longest gaps, taken as section boundaries.
big = sorted(gaps, key=lambda g: -g[2])[:len(SECTIONS) - 1]
big = sorted(big, key=lambda g: g[0])
print(f"\nLikely section breaks (the {len(big)} longest pauses):")
bounds = [0.0] + [round((s + e) / 2, 1) for s, e, _ in big] + [round(total, 1)]
for (label, budget), a, b in zip(SECTIONS, bounds, bounds[1:]):
    actual = b - a
    delta = actual - budget
    flag = "  <-- over" if delta > 3 else ("  <-- under" if delta < -3 else "")
    print(f"  {a:6.1f}–{b:6.1f}  {actual:5.1f}s  (script {budget:2d}s, {delta:+5.1f}){flag}  {label}")

print(f"\n  speed-up needed to reach {TARGET:.0f}s: {total / TARGET:.3f}x "
      f"({(total / TARGET - 1) * 100:.1f}% faster)")
