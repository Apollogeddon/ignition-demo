#!/usr/bin/env python3
"""PreToolUse hook (Read|Edit|Write): exits 2, which blocks the call and tells Claude why, when

- a Read targets a secrets file settings.json's deny list can't name: any *.tfvars but
  *.example.tfvars, any .env but .env.example, backend.hcl, a tfstate;
- an Edit/Write accepts the Ignition EULA in an example file (users copy those as they are);
- an Edit/Write puts a token, private key or API key into a file git doesn't ignore.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

EULA = re.compile(r"^\s*(accept_eula\s*=\s*true|ACCEPT_IGNITION_EULA\s*[=:]\s*[\"']?Y)", re.MULTILINE)
SECRETS = {
    "a GitHub token": re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})"),
    "a private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "an AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "a kubeconfig credential": re.compile(r"(client-key-data|token):\s*[\"']?[A-Za-z0-9+/=._-]{40,}"),
    "a gateway API key": re.compile(
        r"(GATEWAY_API_TOKEN|IGNITION_TOKEN|ignition_token)\s*[=:]\s*[\"']?[\w.-]+:[A-Za-z0-9_-]{43}\b"
    ),
}


def secret_file(name: str) -> bool:
    if name.endswith(".tfvars"):
        return not name.endswith(".example.tfvars")
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    return name == "backend.hcl" or ".tfstate" in name


def ignored(path: Path) -> bool:
    try:
        # git resolved via PATH; the path comes from Claude Code's own tool_input
        result = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=ROOT, check=False)  # noqa: S603, S607
    except OSError:
        return False
    return result.returncode == 0


def block(reason: str) -> None:
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool, tool_input = data.get("tool_name", ""), data.get("tool_input", {})
    file = tool_input.get("file_path")
    if not file:
        return
    path = (ROOT / file).resolve()

    if tool == "Read":
        if secret_file(path.name):
            block(f"{path.name} holds secrets and is not to be read; read its .example instead.")
        return

    content = tool_input.get("content") or tool_input.get("new_string") or ""
    if ".example" in path.name and EULA.search(content):
        block(
            f"{path.name} is an example users copy as is: keep the EULA acceptance commented out, "
            "as only the user may accept the Ignition EULA."
        )
    if not ignored(path):
        for what, pattern in SECRETS.items():
            if pattern.search(content):
                block(
                    f"This writes {what} into {path.name}, which git doesn't ignore. Use a placeholder, "
                    "or a git-ignored file (terraform.tfvars, develop/.env) or a TF_VAR_ variable."
                )


if __name__ == "__main__":
    main()
