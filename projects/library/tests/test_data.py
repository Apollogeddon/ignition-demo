"""Tests for library.data."""

from library.data.code import toRows


class FakeDataset:
	"""The parts of an Ignition Dataset that library.data reads."""

	def __init__(self, columns: list[str], values: list[list[object]]) -> None:
		self.columns = columns
		self.values = values

	def getColumnNames(self) -> list[str]:
		return self.columns

	def getRowCount(self) -> int:
		return len(self.values)

	def getValueAt(self, row: int, column: str) -> object:
		return self.values[row][self.columns.index(column)]


def test_rows_are_keyed_by_column() -> None:
	dataset = FakeDataset(["id", "name"], [[1, "Pump"], [2, "Fan"]])
	assert toRows(dataset) == [{"id": 1, "name": "Pump"}, {"id": 2, "name": "Fan"}]  # type: ignore[arg-type]


def test_empty_dataset() -> None:
	assert toRows(FakeDataset(["id"], [])) == []  # type: ignore[arg-type]
