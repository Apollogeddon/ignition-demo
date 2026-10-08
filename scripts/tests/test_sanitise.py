"""Tests for the resource.json sanitiser."""

from __future__ import annotations

import json
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

# the same resource as an 8.1 gateway rewrites it: other actor, keys moved,
# no final newline
GATEWAY_81 = (
    '{\n  "version": 1,\n  "scope": "G",\n  "files": [\n    "view.json"\n  ],\n'
    '  "attributes": {\n    "lastModificationSignature": "abc",\n'
    '    "lastModification": {\n      "timestamp": "2026-10-08T00:48:09Z",\n      "actor": "external"\n    }\n  }\n}'
)


def test_noisy_fields_get_fixed_values() -> None:
    resource = json.loads(sanitise(DESIGNER))
    assert resource["attributes"]["lastModification"] == {"actor": "system", "timestamp": "2025-01-01T00:00:00Z"}
    assert resource["attributes"]["lastModificationSignature"] == SIGNATURE
    assert resource["files"] == ["view.json"]
    assert resource["scope"] == "G"


def test_designer_and_gateway_rewrites_give_the_same_file() -> None:
    assert sanitise(DESIGNER) == sanitise(GATEWAY_81)


def test_canonical_form_is_stable() -> None:
    clean = sanitise(DESIGNER)
    assert sanitise(clean) == clean
    assert clean.endswith("}\n")
    assert clean.startswith('{\n  "attributes"')


def test_only_the_thumbnail_leaves_files() -> None:
    assert json.loads(sanitise('{"files": ["thumbnail.png"]}'))["files"] == []
    assert json.loads(sanitise('{"files": ["thumbnail.png", "view.json"]}'))["files"] == ["view.json"]


def test_signature_is_not_added_where_there_was_none() -> None:
    assert "lastModificationSignature" not in sanitise('{"attributes": {"enabled": true}}')


def test_non_json_is_left_alone() -> None:
    assert sanitise("not json") == "not json"
    assert sanitise("[1, 2]") == "[1, 2]"


def test_check_and_fix(tmp_path: Path) -> None:
    f = tmp_path / "resource.json"
    f.write_text(DESIGNER)
    assert main(["--check", str(f)]) == 1
    assert main(["--fix", str(f)]) == 0
    assert main(["--check", str(f)]) == 0
