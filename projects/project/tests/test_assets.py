"""Tests for project.assets."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from project.assets.code import buildInstances, getSummary, summarise, syncInstances


def test_summarise_counts_per_area_largest_first() -> None:
	rows = [
		{"area": "North"},
		{"area": "South"},
		{"area": "South"},
		{"area": None},
		{"area": "East"},
	]
	assert summarise(rows) == [
		{"area": "South", "count": 2},
		{"area": "East", "count": 1},
		{"area": "North", "count": 1},
		{"area": "Unassigned", "count": 1},
	]


def test_summarise_nothing() -> None:
	assert summarise([]) == []


def test_get_summary_runs_the_named_query() -> None:
	db: MagicMock = sys.modules["system.db"]  # type: ignore[assignment]
	with patch("project.assets.code.toRows", return_value=[{"area": "North"}]) as toRows:
		assert getSummary() == [{"area": "North", "count": 1}]
	db.execQuery.assert_called_once_with("assets/list", {})
	toRows.assert_called_once_with(db.execQuery.return_value)


ROWS = [
	{"name": "Intake pump 1", "area": "North", "kind": "pump"},
	{"name": "Blower 1", "area": "South", "kind": "blower"},
	{"name": "Spare", "area": None, "kind": "pump"},
	{"name": "Mystery", "area": "East", "kind": "teleporter"},
]


def test_build_instances_groups_by_area_and_skips_unknown_kinds() -> None:
	assert buildInstances(ROWS, ["pump", "blower"]) == {
		"North": [{"name": "Intake pump 1", "tagType": "UdtInstance", "typeId": "equipment/pump"}],
		"South": [{"name": "Blower 1", "tagType": "UdtInstance", "typeId": "equipment/blower"}],
		"Unassigned": [{"name": "Spare", "tagType": "UdtInstance", "typeId": "equipment/pump"}],
	}


def test_sync_instances_merges_each_area_folder() -> None:
	tag: MagicMock = sys.modules["system.tag"]  # type: ignore[assignment]
	with patch("project.assets.code.toRows", return_value=ROWS):
		assert syncInstances("plant") == 3
	paths = [c.args[0] for c in tag.configure.call_args_list]
	assert paths == ["[plant]Assets/North", "[plant]Assets/South", "[plant]Assets/Unassigned"]
	assert {c.args[2] for c in tag.configure.call_args_list} == {"m"}


def test_default_kinds_match_the_library_udts() -> None:
	index = json.loads(
		Path(__file__).resolve().parents[2].joinpath("library/src/udts/index.json").read_text()
	)
	equipment = sorted(e.split("/")[1] for e in index if e.startswith("equipment/"))
	assert sorted(syncInstances.__defaults__[1]) == equipment  # type: ignore[index]
