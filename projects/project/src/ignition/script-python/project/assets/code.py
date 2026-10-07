"""Asset queries and summaries for the overview views."""

import sys

from library.data import toRows
from system.db import execQuery
from system.util import getLogger

LOGGER = getLogger("demo.project.assets")

if sys.version_info.major >= 3:
	from typing import Any, Dict, Iterable, List


def summarise(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Count assets per area, largest first, then by area name."""
	counts = {}  # type: Dict[str, int]
	for row in rows:
		area = row["area"] or "Unassigned"
		counts[area] = counts.get(area, 0) + 1
	ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
	return [{"area": area, "count": count} for area, count in ordered]


def getSummary():
	# type: (...) -> List[Dict[str, Any]]
	"""Run the assets/list named query and summarise it per area."""
	summary = summarise(toRows(execQuery("assets/list", {})))
	LOGGER.debug("Summarised {} areas".format(len(summary)))
	return summary
