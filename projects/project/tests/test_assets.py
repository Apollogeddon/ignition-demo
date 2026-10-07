"""Tests for project.assets."""

import sys
from unittest.mock import MagicMock, patch

from project.assets.code import getSummary, summarise


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
