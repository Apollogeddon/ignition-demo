"""Tests for library.data."""

from unittest.mock import MagicMock

from library.data.code import toRows


def fake_dataset(columns: list[str], values: list[list[object]]) -> MagicMock:
	"""Return the parts of an Ignition Dataset that library.data reads."""
	dataset = MagicMock(name="Dataset")
	dataset.getColumnNames.return_value = columns
	dataset.getRowCount.return_value = len(values)
	dataset.getValueAt.side_effect = lambda row, column: values[row][columns.index(column)]
	return dataset


def test_rows_are_keyed_by_column() -> None:
	dataset = fake_dataset(["id", "name"], [[1, "Pump"], [2, "Fan"]])
	assert toRows(dataset) == [{"id": 1, "name": "Pump"}, {"id": 2, "name": "Fan"}]


def test_empty_dataset() -> None:
	assert toRows(fake_dataset(["id"], [])) == []
