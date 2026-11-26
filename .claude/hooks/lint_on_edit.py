#!/usr/bin/env python3
"""PostToolUse hook (Edit|Write): formats and lints the edited file with the repository's own
tools, exiting 2 with what it can't fix so it reaches Claude (plain stdout only reaches the
transcript). A tool that isn't installed is skipped quietly: CI runs every check.

    *.tf, *.tftest.hcl, *.tfvars    tofu fmt
    projects/**/*.py(i)             ruff check --fix, then ruff format (projects' uv env)
    *.sh                            shellcheck
    .github/workflows/*.yml         actionlint
    projects/**/resource.json       scripts/sanitise.py --check
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def run(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    # tools resolved via PATH; the file comes from Claude Code's own tool_input
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603


def fail(output: str) -> None:
    sys.stderr.write(output)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    file = data.get("tool_input", {}).get("file_path") or data.get("tool_response", {}).get("filePath")
    if not file:
        return
    path = (ROOT / file).resolve()
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return
    if not path.is_file():
        return
    parts, name = rel.parts, path.name

    if name.endswith((".tf", ".tftest.hcl", ".tfvars")):
        if shutil.which("tofu"):
            result = run(["tofu", "fmt", "-no-color", str(rel)])
            if result.returncode != 0:
                fail(result.stdout + result.stderr)
    elif parts[0] == "projects" and name.endswith((".py", ".pyi")):
        target = str(path.relative_to(ROOT / "projects"))
        check = run(["uv", "run", "--no-sync", "ruff", "check", "--fix", target], ROOT / "projects")
        run(["uv", "run", "--no-sync", "ruff", "format", target], ROOT / "projects")
        if check.returncode != 0:
            fail(check.stdout + check.stderr)
    elif name.endswith(".sh"):
        if shutil.which("shellcheck"):
            result = run(["shellcheck", str(rel)])
            if result.returncode != 0:
                fail(result.stdout + result.stderr)
    elif parts[:2] == (".github", "workflows") and name.endswith((".yml", ".yaml")):
        if shutil.which("actionlint"):
            result = run(["actionlint", "-no-color", str(rel)])
            if result.returncode != 0:
                fail(result.stdout + result.stderr)
    elif parts[0] == "projects" and name == "resource.json":
        result = run([sys.executable, "scripts/sanitise.py", "--check", str(rel)])
        if result.returncode != 0:
            fail(result.stdout + result.stderr)


if __name__ == "__main__":
    main()
