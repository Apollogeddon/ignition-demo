"""Shape asset data for the Overview page: KPI cards, area cards and charts.

Every function here takes rows and returns plain dictionaries and lists, so
the page's bindings stay one-line calls and the shaping is tested in CPython.
"""

import time

from library.data import toRows
from library.db import namedQuery
from library.format import EM_DASH, duration, percent
from project.assets import getStatus, tableRows

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List, Optional

# the plant's areas in display order, and the colour each has on every chart
AREAS = ("North", "South", "East")
AREA_COLORS = {"North": "#2563EB", "South": "#0D9488", "East": "#D97706"}
OTHER_COLOR = "#64748B"


def areaColor(
	area,  # type: str
):
	# type: (...) -> str
	"""Return an area's chart colour; areas outside AREAS share a grey."""
	return AREA_COLORS.get(area, OTHER_COLOR)


def areaOrder(
	area,  # type: str
):
	# type: (...) -> Any
	"""Sort key: the known areas in AREAS order, then any others by name."""
	if area in AREAS:
		return (0, AREAS.index(area), "")
	return (1, 0, area)


def isPumping(
	row,  # type: Dict[str, Any]
):
	# type: (...) -> bool
	"""Whether a row is an online pump, whose reading counts towards pumped flow."""
	return row["kind"] == "pump" and bool(row["online"])


def ago(
	millis,  # type: Optional[float]
	nowMs,  # type: float
):
	# type: (...) -> str
	"""Describe an epoch-milliseconds time relative to now, e.g. "2h 05m ago"."""
	if millis is None:
		return EM_DASH
	return "{} ago".format(duration((nowMs - millis) / 1000.0))


def kpis(
	rows,  # type: List[Dict[str, Any]]
	nowMs,  # type: float
):
	# type: (...) -> Dict[str, Any]
	"""Return the KPI cards' values from assets/status rows."""
	total = len(rows)
	online = sum(1 for row in rows if row["online"])
	events = [row["event_ms"] for row in rows if row["event_ms"] is not None]
	lastEvent = max(events) if events else None
	flow = sum(row["value"] or 0.0 for row in rows if isPumping(row))
	return {
		"total": total,
		"online": online,
		"offline": total - online,
		"availability": percent(float(online) / total) if total else EM_DASH,
		"flow": "{:.1f}".format(flow),
		"lastEvent": lastEvent,
		"lastEventAgo": ago(lastEvent, nowMs) if lastEvent is not None else "No events yet",
	}


def areas(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Return one card per area: its asset counts, pumped flow and colour."""
	cards = {}  # type: Dict[str, Dict[str, Any]]
	for row in rows:
		name = row["area"] or "Unassigned"
		card = cards.setdefault(
			name,
			{
				"area": name,
				"description": row.get("area_description") or "",
				"color": areaColor(name),
				"count": 0,
				"online": 0,
				"offline": 0,
				"flow": 0.0,
			},
		)
		card["count"] += 1
		card["online" if row["online"] else "offline"] += 1
		if isPumping(row):
			card["flow"] += row["value"] or 0.0
	ordered = sorted(cards.values(), key=lambda card: areaOrder(card["area"]))
	for card in ordered:
		card["flow"] = "{:.1f}".format(card["flow"])
	return ordered


def pie(
	cards,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Return the pie chart's data and matching colours from the area cards."""
	cards = list(cards)
	return {
		"data": [{"label": card["area"], "value": card["count"]} for card in cards],
		"colors": [card["color"] for card in cards],
	}


def overview(
	rows,  # type: List[Dict[str, Any]]
	nowMs,  # type: float
):
	# type: (...) -> Dict[str, Any]
	"""Return everything the Overview page shows from one assets/status query."""
	cards = areas(rows)
	summary = kpis(rows, nowMs)
	summary["areas"] = len(cards)
	return {
		"kpis": summary,
		"areas": cards,
		"pie": pie(cards),
		"assets": tableRows(rows),
	}


def getOverview():
	# type: (...) -> Dict[str, Any]
	"""Query the assets' status and shape it for the Overview page."""
	return overview(getStatus(), time.time() * 1000)


def areaAssets(
	assets,  # type: Iterable[Any]
	area,  # type: str
):
	# type: (...) -> List[Any]
	"""Return the asset table rows of one area."""
	return [row for row in assets if row["area"] == area]


def flowSeries(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Pivot readings/flowByArea rows ({time, area, flow}) into chart points.

	Each point is {"time": ms, "<area>": flow, ...} with every area seen in
	the rows; an hour missing an area's flow reads zero, so stacked areas
	stay continuous.
	"""
	rows = list(rows)
	names = sorted({row["area"] for row in rows}, key=areaOrder)
	points = {}  # type: Dict[Any, Dict[str, Any]]
	for row in rows:
		point = points.get(row["time"])
		if point is None:
			point = dict.fromkeys(names, 0.0)
			point["time"] = row["time"]
			points[row["time"]] = point
		point[row["area"]] = row["flow"]
	return [points[key] for key in sorted(points)]


def getFlowSeries():
	# type: (...) -> List[Dict[str, Any]]
	"""Query the pumped flow per area for the Overview page's trend."""
	return flowSeries(toRows(namedQuery("readings/flowByArea")))


def release(
	version,  # type: Any
):
	# type: (...) -> str
	"""Name an Ignition release from system.util.getVersion(), e.g. "Ignition 8.3.10"."""
	return "Ignition {}.{}.{}".format(version.getMajor(), version.getMinor(), version.getRevision())


def gatewayRelease():
	# type: (...) -> str
	"""Name the gateway's release, for the header."""
	from system.util import getVersion

	return release(getVersion())
