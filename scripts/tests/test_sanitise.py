"""Tests for the resource.json sanitiser."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sanitise import SIGNATURE, main, sanitise

DESIGNER = """{
  "scope": "G",
  "version": 1,
  "files": [
    "view.json",
    "thumbnail.png"
  ],
  "attributes": {
    "lastModification": {
      "actor": "jane.doe",
      "timestamp": "2026-10-07T09:47:28Z"
    },
    "lastModificationSignature": "8385e37e27be324afa64c63631aa29c31f707ca724114fc1b02e217172cce47b"
  }
}
"""


def test_noisy_fields_get_fixed_values() -> None:
    clean = sanitise(DESIGNER)
    assert '"actor": "system"' in clean
    assert '"timestamp": "2025-01-01T00:00:00Z"' in clean
    assert f'"lastModificationSignature": "{SIGNATURE}"' in clean
    assert "thumbnail.png" not in clean
    assert '"view.json"\n  ]' in clean


def test_sanitising_is_idempotent_and_keeps_everything_else() -> None:
    clean = sanitise(DESIGNER)
    assert sanitise(clean) == clean
    assert clean.count("\n") == DESIGNER.count("\n") - 1
    assert '"scope": "G"' in clean


def test_thumbnail_anywhere_in_files() -> None:
    assert sanitise('"files": ["thumbnail.png"]') == '"files": []'
    assert sanitise('"files": ["thumbnail.png", "view.json"]') == '"files": ["view.json"]'


def test_check_and_fix(tmp_path: Path) -> None:
    f = tmp_path / "resource.json"
    f.write_text(DESIGNER)
    assert main(["--check", str(f)]) == 1
    assert main(["--fix", str(f)]) == 0
    assert main(["--check", str(f)]) == 0
