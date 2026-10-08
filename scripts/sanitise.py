"""Strip the Designer's and the gateway's noise from Ignition resource.json files.

Every save in the Designer rewrites a resource's lastModification (who and
when) and its lastModificationSignature, and may list a thumbnail.png; a
gateway reading projects from disk (8.1) rewrites them too, reordering keys
and dropping the final newline. None of it changes what the resource does, but
it turns every save into a diff and every merge into a conflict. This writes
each resource.json in one canonical form:

    lastModification.actor      -> "system"
    lastModification.timestamp  -> "2025-01-01T00:00:00Z"
    lastModificationSignature   -> a fixed value
    "thumbnail.png" in files    -> removed
    layout                      -> sorted keys, two-space indent, final newline

Ignition accepts the fixed values and the key order, and rewrites them on its
next save; with the git filter (scripts/setup-git.sh) those rewrites never
show up as changes.

Usage:
    sanitise.py < resource.json           # git clean filter (stdin -> stdout)
    sanitise.py --check FILE...           # exit 1 listing files that need it
    sanitise.py --fix FILE...             # rewrite files in place
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ACTOR = "system"
TIMESTAMP = "2025-01-01T00:00:00Z"
SIGNATURE = "0" * 64


def clean(resource: dict[str, Any]) -> dict[str, Any]:
    """Return the resource with its noisy fields set to fixed values."""
    files = resource.get("files")
    if isinstance(files, list):
        resource["files"] = [f for f in files if f != "thumbnail.png"]
    attributes = resource.get("attributes")
    if isinstance(attributes, dict):
        modification = attributes.get("lastModification")
        if isinstance(modification, dict):
            modification["actor"] = ACTOR
            modification["timestamp"] = TIMESTAMP
        if "lastModificationSignature" in attributes:
            attributes["lastModificationSignature"] = SIGNATURE
    return resource


def sanitise(text: str) -> str:
    """Return a resource.json in canonical form; text that is not a JSON object is returned as-is."""
    try:
        resource = json.loads(text)
    except json.JSONDecodeError:
        return text
    if not isinstance(resource, dict):
        return text
    return json.dumps(clean(resource), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


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
        canonical = sanitise(text)
        if canonical != text:
            dirty.append(path)
            if mode == "--fix":
                path.write_text(canonical, "utf-8", newline="")
    if mode == "--check" and dirty:
        sys.stderr.write("not sanitised (run scripts/sanitise.py --fix):\n")
        sys.stderr.writelines(f"  {p}\n" for p in dirty)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
