"""Query tag history on Ignition 8.1 and 8.3.

8.3 queries its historians with system.historian.queryAggregatedPoints; 8.1
has system.tag.queryTagHistory. Scripts call library.history.averages and get
whichever the gateway provides, as wide rows: {"time": epoch ms, name: value}.
"""

from library.data import toRows

# each import only exists in one version's stubs, hence the pyright ignores
try:
	# Ignition 8.3
	from system.historian import (  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
		queryAggregatedPoints as _queryAggregatedPoints,
	)

	HISTORIAN = True
except ImportError:
	# Ignition 8.1
	from system.tag import (
		queryTagHistory as _queryTagHistory,  # pyright: ignore[reportAttributeAccessIssue]
	)

	HISTORIAN = False

MYPY = False
if MYPY:
	from typing import Any, Dict, List

	from java.util import Date

# the time column of a wide history dataset: 8.1 names it t_stamp, 8.3 timestamp
TIME_COLUMNS = ("t_stamp", "timestamp")


def query(
	paths,  # type: List[str]
	names,  # type: List[str]
	start,  # type: Date
	end,  # type: Date
	points,  # type: int
):
	# type: (...) -> Any
	"""Return a wide dataset of each path's average over points intervals of start..end."""
	if HISTORIAN:
		return _queryAggregatedPoints(  # pyright: ignore[reportPossiblyUnboundVariable]
			paths,
			startTime=start,
			endTime=end,
			aggregates=["Average"] * len(paths),
			columnNames=names,
			returnFormat="Wide",
			returnSize=points,
		)
	return _queryTagHistory(  # pyright: ignore[reportPossiblyUnboundVariable]
		paths=paths,
		startDate=start,
		endDate=end,
		returnSize=points,
		aggregationMode="Average",
		returnFormat="Wide",
		columnNames=names,
		ignoreBadQuality=True,
	)


def toPoints(
	rows,  # type: List[Dict[str, Any]]
	names,  # type: List[str]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Turn wide history rows into {"time": ms, name: value} points.

	Columns are matched without regard to case: 8.3 lowercases the column
	names it is given. A value the historian has no data for (None) is left
	out, so a chart's line breaks there instead of dropping to zero.
	"""
	result = []  # type: List[Dict[str, Any]]
	for source in rows:
		row = {str(key).lower(): value for key, value in source.items()}
		stamp = [row[column] for column in TIME_COLUMNS if row.get(column) is not None]
		if not stamp:
			continue
		point = {"time": stamp[0].getTime()}  # type: Dict[str, Any]
		for name in names:
			value = row.get(name.lower())
			if value is not None:
				point[name] = round(float(value), 1)
		result.append(point)
	return result


def averages(
	paths,  # type: List[str]
	names,  # type: List[str]
	start,  # type: Date
	end,  # type: Date
	points,  # type: int
):
	# type: (...) -> List[Dict[str, Any]]
	"""Query each path's averages over start..end as chart points named by names."""
	return toPoints(toRows(query(paths, names, start, end, points)), names)
