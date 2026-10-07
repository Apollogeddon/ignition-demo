"""Dataset helpers shared by every project."""

import sys

if sys.version_info.major >= 3:
	from typing import TYPE_CHECKING, Any, Dict, List

	# Java classes exist only as stubs outside the gateway
	if TYPE_CHECKING:
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
