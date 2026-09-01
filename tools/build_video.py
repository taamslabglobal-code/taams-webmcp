# -*- coding: utf-8 -*-
"""Assemble the demo video from the three takes, per EDIT-SHEET.md.

Cuts each segment, normalises them onto one 1920x1080 30fps canvas, burns in the
five captions, lays the narration over the whole thing, and writes one mp4.

The agent take is 1088x896 — a different aspect from the two 1920x1080 human
takes — so it is pillarboxed rather than cropped. Cropping it would cut into the
comparison board, which is the one thing the video exists to show.

    python tools/build_video.py [narration file]

Every timestamp traces to EDIT-SHEET.md. The one thing that is *not* fixed is
the closing freeze: it is computed from the narration so the picture always
outlasts the voice. Hard-coding it once cut the last sentence off, and a value
that has to be re-tuned by hand every time the audio changes will eventually be
wrong again.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "shots" / "build"
WORK.mkdir(parents=True, exist_ok=True)

TAKE_A = ROOT / "shots" / "video" / "takeA-human-search.mp4"
TAKE_C = ROOT / "shots" / "video" / "takeC-human-clicks.mp4"
TAKE_B = pathlib.Path(r"C:/Users/glone/Videos/Captures/ChatGPT 2026-09-01 22-20-16.mp4")
NARRATION = pathlib.Path(r"C:/WORK/trim_0.35.m4a")
OUT = ROOT / "shots" / "TAAMs-WebMCP-demo.mp4"

W, H, FPS = 1920, 1080, 30

# Screen recordings are the hard case for a codec: hard edges, small text, flat
# colour. Three things were costing quality here.
#
#  1. Every segment was written at CRF 20 and then the join was re-encoded at
#     19 — two lossy generations, and the first one is where the text softened.
#     Intermediates are now near-lossless; the final pass is the only lossy one.
#  2. The scaler defaulted to bicubic, which blurs on the way up. The agent take
#     is 1088x896 going to 1080 tall, so it is scaling up, and lanczos keeps the
#     letterforms.
#  3. CRF 19 is a fine number for camera footage and too coarse for a page of
#     4pt table rows.
CRF_INTERMEDIATE = "12"    # visually lossless working copies
CRF_FINAL = "15"
SCALE_FLAGS = "flags=lanczos+accurate_rnd+full_chroma_int"
FONT = "C\\:/Windows/Fonts/segoeui.ttf"        # ffmpeg wants the colon escaped
FONT_B = "C\\:/Windows/Fonts/segoeuib.ttf"

# (source, start, duration, zoom) — from EDIT-SHEET.md. Order is the cut order.
#
# The human takes were recorded at 1920x1080, so dropping them onto a 1920x1080
# canvas leaves every control at its native size — legible on a monitor, too
# small in a video a judge watches in a window. They get zoomed into the part
# that matters. The agent take is already smaller than the canvas, so it is
# pillarboxed at 1.0 rather than blown up.
#
# Shortening the opening freed 14s that has to go back into the body — left in
# the closing freeze it would have become half a minute of a still image.
# It went to the two stretches that reward dwelling: the cards landing, and the
# approval modal being read.
SEGMENTS = [
    ("A", TAKE_A, 0.0, 20.0, 1.45),     # person searches — zoom on search + card
    ("B1", TAKE_B, 30.0, 12.0, 1.0),    # badge + question 1 on screen
    ("B2", TAKE_B, 42.0, 26.0, 1.0),    # lookups landing
    ("B3", TAKE_B, 74.0, 30.0, 1.0),    # cards appear, highlight follows <- the entry
    ("B4", TAKE_B, 118.0, 41.0, 1.0),   # question 2 -> approval modal, held
    ("C", TAKE_C, 8.0, 20.0, 1.35),     # person does the same by hand
]
FREEZE_AT = 90.0                   # B, both cards on the board
TAIL = 1.5                         # picture held after the voice stops
LIMIT = 180.0                      # contest hard limit
MIN_FREEZE = 8.0                   # the closing shot still has to read as a shot

# Devpost's own advice: "show your project working in the first 15 seconds."
# The opening was 26s of text on black, which put the first working screen at
# 0:26. Cut to 12s: the two questions still land, and the page arrives inside
# the window judges are told to watch.
OPENING = 12.0


def run(args, **kw):
    subprocess.run(args, check=True, **kw)


def esc(text: str) -> str:
    """drawtext eats colons, apostrophes and backslashes."""
    return text.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\\'")


def title_card(path: pathlib.Path) -> None:
    """The opening: no page yet, just the two questions and then the three words.

    Deliberately not stock footage — a montage would need licensing, and text on
    black reads faster anyway.
    """
    lines = [
        # (text, size, y, appear, disappear)
        ("Is this a real supplier?", 74, "(h/2)-90", 0.6, 11.6),
        ("Is this a real price?", 74, "(h/2)+10", 2.6, 11.6),
        ("Today: customs portals, cold calls, guesswork.", 38, "(h/2)+140", 5.6, 11.6),
    ]
    draws = []
    for text, size, y, t0, t1 in lines:
        colour = "white" if size >= 70 else "0xC7CCD6"
        draws.append(
            f"drawtext=fontfile='{FONT}':text='{esc(text)}':"
            f"fontsize={size}:fontcolor={colour}:x=(w-text_w)/2:y={y}:"
            f"enable='between(t,{t0},{t1})':alpha='min(1,(t-{t0})*1.6)'"
        )
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=0x0B0E14:s={W}x{H}:r={FPS}:d={OPENING}",
         "-vf", ",".join(draws), "-c:v", "libx264", "-preset", "fast",
         "-crf", CRF_INTERMEDIATE, "-pix_fmt", "yuv420p", str(path)])


def normalise(src: pathlib.Path, start: float, dur: float, out: pathlib.Path,
              zoom: float = 1.0) -> None:
    """One canvas, one frame rate. Pillarbox rather than crop — see module docs.

    `zoom` > 1 crops into the top-left working area before scaling: on the human
    takes that is the search box, the product card and the board, which is where
    the action is. Anchored high and left rather than centred, because centring
    a 16:9 crop lands on empty page.
    """
    crop = f"crop=iw/{zoom}:ih/{zoom}:0:0," if zoom > 1.0 else ""
    vf = (f"{crop}"
          f"scale={W}:{H}:force_original_aspect_ratio=decrease:{SCALE_FLAGS},"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0B0E14,fps={FPS},setsar=1")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(start), "-i", str(src), "-t", str(dur),
         "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast",
         "-crf", CRF_INTERMEDIATE, "-pix_fmt", "yuv420p", str(out)])


def freeze(src: pathlib.Path, at: float, dur: float, out: pathlib.Path) -> None:
    still = WORK / "_freeze.png"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", str(at), "-i", str(src), "-frames:v", "1", str(still)])
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:{SCALE_FLAGS},"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0B0E14,setsar=1,"
          f"drawtext=fontfile='{FONT_B}':text='taams-sourcing-desk.netlify.app':"
          f"fontsize=44:fontcolor=white:box=1:boxcolor=0x0B0E14@0.85:boxborderw=18:"
          f"x=(w-text_w)/2:y=h-190:enable='gte(t,1.5)',"
          f"drawtext=fontfile='{FONT}':text='MIT licensed':"
          f"fontsize=30:fontcolor=0xC7CCD6:x=(w-text_w)/2:y=h-120:enable='gte(t,2.5)'")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-loop", "1", "-i", str(still), "-t", str(dur), "-r", str(FPS),
         "-vf", vf, "-c:v", "libx264", "-preset", "fast",
         "-crf", CRF_INTERMEDIATE, "-pix_fmt", "yuv420p", str(out)])


# Captions, on the final timeline. Four only — see EDIT-SHEET.md.
#
# These are absolute times into the finished cut, so they move whenever a
# segment length does. Segment boundaries with the current SEGMENTS:
#   open 0-12 · A 12-32 · B1 32-44 · B2 44-70 · B3 70-100 · B4 100-141 · C 141-161
CAPTIONS = [
    ("Tier A  -  lookup", 16.0, 22.0),
    ("Tier B  -  screen control", 73.0, 80.0),
    ("0 network requests", 84.0, 91.0),
    ("Tier C  -  human approval", 106.0, 113.0),
]


def caption_filter() -> str:
    out = []
    for text, t0, t1 in CAPTIONS:
        out.append(
            f"drawtext=fontfile='{FONT_B}':text='{esc(text)}':fontsize=40:"
            f"fontcolor=white:box=1:boxcolor=0x1D4ED8@0.92:boxborderw=16:"
            f"x=64:y=h-140:enable='between(t,{t0},{t1})'"
        )
    return ",".join(out)


def probe(path: pathlib.Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True).stdout.strip())


def main() -> int:
    global NARRATION
    if len(sys.argv) > 1:
        NARRATION = pathlib.Path(sys.argv[1])

    for p, label in ((TAKE_A, "take A"), (TAKE_C, "take C"),
                     (TAKE_B, "take B"), (NARRATION, "narration")):
        if not p.exists():
            print(f"missing {label}: {p}")
            return 1

    # Fit the closing freeze to the voice rather than to a number typed once.
    voice = probe(NARRATION)
    body = OPENING + sum(s[3] for s in SEGMENTS)
    freeze_len = max(MIN_FREEZE, voice + TAIL - body)
    total = body + freeze_len
    print(f"narration {voice:.1f}s · body {body:.1f}s · freeze {freeze_len:.1f}s"
          f" -> {total:.1f}s")
    if total > LIMIT:
        over = total - LIMIT
        print(f"\nthat is {over:.1f}s over the {LIMIT:.0f}s limit.")
        print(f"the narration needs to come in under {LIMIT - MIN_FREEZE - body + TAIL:.0f}s,")
        print("or a segment in SEGMENTS has to be shortened. Not building.")
        return 1

    parts = []
    print("building opening")
    op = WORK / "00-open.mp4"
    title_card(op)
    parts.append(op)

    for i, (label, src, start, dur, zoom) in enumerate(SEGMENTS, 1):
        out = WORK / f"{i:02d}-{label}.mp4"
        print(f"cutting {label}: {start:.0f}s +{dur:.0f}s"
              + (f"  zoom x{zoom}" if zoom > 1 else ""))
        normalise(src, start, dur, out, zoom)
        parts.append(out)

    print("building freeze ending")
    fr = WORK / "99-freeze.mp4"
    freeze(TAKE_B, FREEZE_AT, freeze_len, fr)
    parts.append(fr)

    listing = WORK / "concat.txt"
    listing.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")

    silent = WORK / "silent.mp4"
    print("joining")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c", "copy", str(silent)])

    print("captions + narration")
    # No -shortest: the picture is the longer of the two on purpose, and the
    # flag would trim whichever ended first — which is how the last sentence of
    # narration went missing. A short fade keeps the tail from clicking.
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(silent), "-i", str(NARRATION),
         "-vf", caption_filter(),
         "-af", f"afade=t=out:st={max(0.0, voice - 0.7):.2f}:d=0.7",
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", CRF_FINAL,
         "-x264-params", "aq-mode=3:psy-rd=0.4:deblock=-1,-1",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         str(OUT)])

    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(OUT)],
        capture_output=True, text=True).stdout.strip()
    d = float(dur)
    print(f"\n{OUT}")
    print(f"  {d:.1f}s  ({int(d // 60)}:{d % 60:04.1f})  "
          + ("OK under 3:00" if d < 180 else f"OVER by {d - 180:.1f}s"))
    return 0 if d < 180 else 1


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    sys.exit(main())
