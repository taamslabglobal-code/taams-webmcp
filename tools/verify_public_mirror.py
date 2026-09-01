# -*- coding: utf-8 -*-
"""Byte-compare the tested repo against the one about to be published.

The two repositories are built separately on purpose — the private one keeps the
messy history, the public one starts clean — and that separation is exactly what
lets them drift. Publishing a file that was never the file under test is the
failure this guards against.

    python tools/verify_public_mirror.py <private dir> <public dir>

Exit 0 only when the tracked file sets and every file's hash match.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def tracked(repo: pathlib.Path) -> dict[str, str]:
    names = subprocess.run(["git", "-C", str(repo), "ls-files"],
                           capture_output=True, text=True, check=True).stdout.split()
    out = {}
    for n in names:
        p = repo / n
        if p.is_file():
            out[n] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    if len(sys.argv) < 3:
        return int(bool(sys.exit(__doc__.strip().splitlines()[-3].strip())))
    priv, pub = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    a, b = tracked(priv), tracked(pub)

    only_priv = sorted(set(a) - set(b))
    only_pub = sorted(set(b) - set(a))
    differ = sorted(k for k in set(a) & set(b) if a[k] != b[k])

    print(f"tested   {priv}  {len(a)} files")
    print(f"publish  {pub}  {len(b)} files\n")

    if only_priv:
        print("in the tested repo but NOT being published:")
        for k in only_priv:
            print(f"  - {k}")
    if only_pub:
        print("being published but NEVER TESTED:")
        for k in only_pub:
            print(f"  + {k}")
    if differ:
        print("same name, different bytes — the published copy is not what was tested:")
        for k in differ:
            print(f"  ! {k}")

    ok = not (only_priv or only_pub or differ)
    print(("\nidentical — everything being published is what was tested"
           if ok else "\nMISMATCH — do not publish until this is resolved"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
