"""Tests for library.history on both Ignition versions."""

import importlib
import sys
from unittest.mock import MagicMock

import pytest
from library.history import code


class Stamp:
	def __init__(self, ms: int) -> None:
		self.ms = ms

	def getTime(self) -> int:
		return self.ms


def test_points_match_columns_without_case_and_skip_gaps() -> None:
	rows = [
		{"t_stamp": Stamp(1000), "well": 50.04, "reservoir": None},
		{"timestamp": Stamp(2000), "Well": 51.0, "Reservoir": 70.0},
		{"t_stamp": None, "well": 1.0},
	]
	assert code.toPoints(rows, ["Well", "Reservoir"]) == [
		{"time": 1000, "Well": 50.0},
		{"time": 2000, "Well": 51.0, "Reservoir": 70.0},
	]


def test_queries_aggregated_points_on_8_3(system: dict[str, MagicMock]) -> None:
	historian = system["system.historian"]
	importlib.reload(code)
	start, end = MagicMock(name="start"), MagicMock(name="end")
	code.query(["a", "b"], ["A", "B"], start, end, 60)
	historian.queryAggregatedPoints.assert_called_once_with(
		["a", "b"],
		startTime=start,
		endTime=end,
		aggregates=["Average", "Average"],
		columnNames=["A", "B"],
		returnFormat="Wide",
		returnSize=60,
	)


def test_falls_back_to_query_tag_history_on_8_1(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.delitem(sys.modules, "system.historian")
	tag = sys.modules["system.tag"]
	importlib.reload(code)
	try:
		code.query(["a"], ["A"], MagicMock(), MagicMock(), 10)
		kwargs = tag.queryTagHistory.call_args.kwargs
		assert kwargs["aggregationMode"] == "Average"
		assert kwargs["columnNames"] == ["A"]
		assert kwargs["returnSize"] == 10
	finally:
		monkeypatch.undo()
		importlib.reload(code)
