"""Tests for project.assets."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from project.assets import code
from project.assets.code import (
	buildInstances,
	detail,
	getDetail,
	getSummary,
	getTable,
	live,
	reading,
	summarise,
	syncInstances,
	tableRows,
)


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
	with (
		patch("project.assets.code.namedQuery") as namedQuery,
		patch("project.assets.code.toRows", return_value=[{"area": "North"}]) as toRows,
	):
		assert getSummary() == [{"area": "North", "count": 1}]
	namedQuery.assert_called_once_with("assets/list")
	toRows.assert_called_once_with(namedQuery.return_value)


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


def test_sync_instances_merges_each_area_folder(system: dict[str, MagicMock]) -> None:
	tag = system["system.tag"]
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
	kinds = inspect.signature(syncInstances).parameters["kinds"].default
	assert sorted(kinds) == equipment


STATUS = [
	{
		"id": 1,
		"name": "Intake pump 1",
		"area": "North",
		"kind": "pump",
		"online": True,
		"unit": "L/s",
		"value": 42.345,
		"event_ms": None,
	},
	{
		"id": 3,
		"name": "Blower 1",
		"area": "South",
		"kind": "blower",
		"online": False,
		"unit": "m³/h",
		"value": 1450.4,
		"event_ms": 1000,
	},
]


@pytest.mark.parametrize(
	("value", "unit", "text"),
	[(42.345, "L/s", "42.3 L/s"), (1450.4, "rpm", "1,450 rpm"), (None, "L/s", "—"), (3, "", "3.0")],
)
def test_reading(value: float | None, unit: str, text: str) -> None:
	assert reading(value, unit) == text


def test_table_rows_show_status_pills_and_readings() -> None:
	rows = tableRows(STATUS)
	assert rows[0] == {
		"id": 1,
		"name": "Intake pump 1",
		"area": "North",
		"kind": "Pump",
		"status": "Online",
		"reading": "42.3 L/s",
		"event": None,
	}
	assert rows[1]["status"] == "Offline"
	assert rows[1]["reading"] == "1,450 m³/h"


def test_get_table_runs_the_status_query() -> None:
	with (
		patch("project.assets.code.namedQuery") as namedQuery,
		patch("project.assets.code.toRows", return_value=STATUS),
	):
		assert [row["id"] for row in getTable()] == [1, 3]
	namedQuery.assert_called_once_with("assets/status")


def test_detail_of_one_asset() -> None:
	events = [{"id": 9, "kind": "note"}]
	result = detail(3, STATUS, [{"time": 5, "value": 1.5, "extra": "x"}], events)
	assert result["found"] is True
	assert result["name"] == "Blower 1"
	assert result["status"] == "Offline"
	assert result["online"] is False
	assert result["reading"] == "1,450 m³/h"
	assert result["readings"] == [{"time": 5, "value": 1.5}]
	assert result["events"] == events


def test_detail_of_an_unknown_asset_is_empty() -> None:
	result = detail(99, STATUS, [], [])
	assert result["found"] is False
	assert result["readings"] == []


EVENT = {
	"id": 1,
	"time": 5,
	"asset": "Blower 1",
	"area": "South",
	"kind": "note",
	"message": "m",
	"operator": "ann",
}


def test_get_detail_queries_readings_events_and_status() -> None:
	with (
		patch("project.assets.code.namedQuery") as namedQuery,
		patch("project.assets.code.toRows", side_effect=[[], [EVENT], STATUS]),
	):
		result = getDetail("3")
	assert result["name"] == "Blower 1"
	assert result["events"][0]["kind"] == "Note"
	assert [c.args for c in namedQuery.call_args_list] == [
		("readings/asset", {"assetId": 3}),
		("events/list", {"assetId": 3, "limit": 5}),
		("assets/status",),
	]


def test_get_detail_without_an_asset_queries_nothing() -> None:
	with patch("project.assets.code.namedQuery") as namedQuery:
		assert getDetail(None)["found"] is False
	namedQuery.assert_not_called()


def test_live_overlays_the_tags_on_the_database_rows() -> None:
	rows = [
		{"name": "Blower 2", "kind": "blower", "online": True, "value": 1300.0},
		{"name": "Reservoir level", "kind": "level", "online": True, "value": 64.0},
		{"name": "Old sensor", "kind": "sensor", "online": True, "value": 1.0},
	]
	values = {
		"Blower 2": {"value": 0.0, "fault": True, "running": False},
		"Reservoir level": {"value": 71.5},
	}
	blower, reservoir, sensor = live(rows, values)
	assert blower["value"] == 0.0
	assert blower["online"] is False
	assert blower["running"] is False
	assert reservoir == {**rows[1], "value": 71.5}
	assert sensor == rows[2]
	# the database's rows are left as they were
	assert rows[0]["online"] is True


def test_status_falls_back_to_the_database_when_tags_fail() -> None:
	rows = [{"name": "Mixer", "area": "South", "kind": "mixer", "online": True, "value": 58.0}]
	with (
		patch.object(code, "namedQuery"),
		patch.object(code, "toRows", return_value=rows),
		patch.object(code, "readValues", side_effect=RuntimeError("provider down")),
		patch.object(code, "LOGGER") as logger,
	):
		assert code.getStatus() == rows
	assert "provider down" in logger.warn.call_args.args[0]


def test_live_keeps_the_database_values_for_unread_tags() -> None:
	rows = [{"name": "Blower 2", "kind": "blower", "online": False, "value": 0.0}]
	assert live(rows, {"Blower 2": {"value": None, "fault": None, "running": None}}) == rows
