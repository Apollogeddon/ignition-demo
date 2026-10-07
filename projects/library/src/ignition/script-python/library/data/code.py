"""Dataset helpers shared by every project."""

MYPY = False
if MYPY:
	from typing import Any, Dict, List

	from com.inductiveautomation.ignition.common import Dataset


def toRows(
	dataset,  # type: Dataset
):
	# type: (...) -> List[Dict[str, Any]]
	"""Return a dataset's rows as dictionaries keyed by column name."""
	columns = list(dataset.getColumnNames())
	return [
		{column: dataset.getValueAt(index, column) for column in columns}
		for index in range(dataset.getRowCount())
	]
