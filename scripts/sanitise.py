"""Strip the Designer's noise from Ignition resource.json files.

Every save in the Designer rewrites a resource's lastModification (who and
when) and its lastModificationSignature, and may list a thumbnail.png. None of
it changes what the resource does, but it turns every save into a diff and every
merge into a conflict. This rewrites those fields to fixed values:

    actor                       -> "system"
    timestamp                   -> "2025-01-01T00:00:00Z"
    lastModificationSignature   -> a fixed value
    "thumbnail.png" in files    -> removed

Only those fields change; the rest of the file is left byte for byte, so the
diff stays minimal. Ignition accepts the fixed values and rewrites them on its
next save.

Usage:
    sanitise.py < resource.json           # git clean filter (stdin -> stdout)
    sanitise.py --check FILE...           # exit 1 listing files that need it
    sanitise.py --fix FILE...             # rewrite files in place
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SIGNATURE = "0" * 64
RULES = (
    (re.compile(r'("actor"\s*:\s*")[^"]*(")'), r"\g<1>system\g<2>"),
    (re.compile(r'("timestamp"\s*:\s*")[^"]*(")'), r"\g<1>2025-01-01T00:00:00Z\g<2>"),
    (re.compile(r'("lastModificationSignature"\s*:\s*")[^"]*(")'), rf"\g<1>{SIGNATURE}\g<2>"),
    (re.compile(r',\s*"thumbnail\.png"'), ""),
    (re.compile(r'"thumbnail\.png"\s*,\s*'), ""),
    (re.compile(r'\[\s*"thumbnail\.png"\s*\]'), "[]"),
)


def sanitise(text: str) -> str:
    """Return the resource with the noisy fields set to fixed values."""
    for pattern, replacement in RULES:
        text = pattern.sub(replacement, text)
    return text


def main(argv: list[str]) -> int:
    """Run as a filter (no arguments), or --check / --fix the given files."""
    if not argv:
        data = sys.stdin.buffer.read().decode("utf-8")
        sys.stdout.buffer.write(sanitise(data).encode("utf-8"))
        return 0
    mode, files = argv[0], [Path(f) for f in argv[1:]]
    if mode not in ("--check", "--fix"):
        sys.stderr.write(__doc__ or "")
        return 2
    dirty = []
    for path in files:
        text = path.read_text("utf-8")
        clean = sanitise(text)
        if clean != text:
            dirty.append(path)
            if mode == "--fix":
                path.write_text(clean, "utf-8", newline="")
    if mode == "--check" and dirty:
        sys.stderr.write("not sanitised (run scripts/sanitise.py --fix):\n")
        sys.stderr.writelines(f"  {p}\n" for p in dirty)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
