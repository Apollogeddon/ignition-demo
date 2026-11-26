"""Shape hourly readings and asset status for the Analytics page.

readings/hourly gives each hour's readings per area and kind; hourly() pivots
them into one point per hour: intake flow (the North pumps), delivered flow
(the East pumps) and the reservoir level (the East level). The page's chart,
heatmap and plant output come from those points, and its gauges and area
bars from assets/status.
"""

from library.data import toRows
from library.db import namedQuery
from library.format import EM_DASH, percent
from library.history import averages
from project.assets import getStatus
from project.overview import areaColor, areaOrder
from system.date import addMinutes, now

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List, Optional

# which area and kind each hourly measure comes from, and whether it sums the
# assets (flows) or averages them (levels)
MEASURES = {
	"intake": ("North", "pump", "total"),
	"delivered": ("East", "pump", "total"),
	"reservoir": ("East", "level", "mean"),
}

# litres per second, held for an hour, in cubic metres
LPS_TO_M3_PER_HOUR = 3.6
HOURS_PER_DAY = 24

# the heatmap's sequential scale, light to dark, and the colour of an hour with no data
HEAT = ("#EFF6FF", "#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6", "#2563EB", "#1D4ED8")
HEAT_EMPTY = "#F8FAFC"
# from this step of HEAT on, a cell's text is white
HEAT_DARK = 5
# hours of the day the heatmap's header labels
HEAT_LABELS = (0, 3, 6, 9, 12, 15, 18, 21)


def hourly(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Pivot readings/hourly rows into one point per hour, oldest first.

	Each point is {time, day, hour, label, intake, delivered, volume,
	reservoir}: flows in L/s, the delivered volume in cubic metres and the level in %.
	A measure with no reading that hour is None.
	"""
	points = {}  # type: Dict[Any, Dict[str, Any]]
	for row in rows:
		point = points.get(row["time"])
		if point is None:
			point = {
				"time": row["time"],
				"day": row["day"],
				"hour": row["hour"],
				"label": "{} {:02d}:00".format(row["day"][:3], row["hour"]),
			}
			point.update(dict.fromkeys(MEASURES))
			points[row["time"]] = point
		for name, (area, kind, column) in MEASURES.items():
			if row["area"] == area and row["kind"] == kind:
				point[name] = row[column]
	ordered = [points[key] for key in sorted(points)]
	for point in ordered:
		delivered = point["delivered"]
		point["volume"] = None if delivered is None else round(delivered * LPS_TO_M3_PER_HOUR, 1)
	return ordered


def chart(
	points,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Return the XY chart's rows: each hour's label, delivered volume and reservoir level."""
	return [
		{"label": point["label"], "volume": point["volume"], "reservoir": point["reservoir"]}
		for point in points
		if point["volume"] is not None or point["reservoir"] is not None
	]


def output(
	points,  # type: List[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Return the water delivered over the last 24 hours of points, in cubic metres."""
	volumes = [point["volume"] for point in points[-HOURS_PER_DAY:] if point["volume"] is not None]
	# round() returns a float on Jython 2.7
	return {"volume": int(round(sum(volumes))), "hours": len(volumes)}  # noqa: RUF046


def heatColor(
	value,  # type: Optional[float]
	low,  # type: float
	high,  # type: float
):
	# type: (...) -> Any
	"""Return a value's step on the HEAT scale between low and high, or None."""
	if value is None:
		return None
	if high <= low:
		return len(HEAT) // 2
	step = int((value - low) / (high - low) * len(HEAT))
	return min(max(step, 0), len(HEAT) - 1)


def heatmap(
	points,  # type: Iterable[Dict[str, Any]]
	measure="intake",  # type: str
	unit="L/s",  # type: str
):
	# type: (...) -> Dict[str, Any]
	"""Return a day-by-hour grid of one measure: a row per day, a cell per hour.

	Each cell is {color, dark, text, tooltip}, the parameters of Cells/HeatCell;
	an hour with no reading is empty and pale. The scale runs from the lowest
	to the highest value seen.
	"""
	points = [point for point in points if point[measure] is not None]
	values = [point[measure] for point in points]
	low = min(values) if values else 0.0
	high = max(values) if values else 0.0
	days = []  # type: List[Dict[str, Any]]
	byDay = {}  # type: Dict[str, Dict[int, float]]
	for point in points:
		if point["day"] not in byDay:
			byDay[point["day"]] = {}
			days.append({"label": point["day"]})
		byDay[point["day"]][point["hour"]] = point[measure]
	for day in days:
		cells = []
		for hour in range(HOURS_PER_DAY):
			value = byDay[day["label"]].get(hour)
			step = heatColor(value, low, high)
			when = "{} {:02d}:00".format(day["label"], hour)
			cells.append(
				{
					"color": HEAT_EMPTY if step is None else HEAT[step],
					"dark": step is not None and step >= HEAT_DARK,
					"text": "" if value is None else "{:.0f}".format(value),
					"tooltip": when
					+ (", no data" if value is None else ", {:.1f} {}".format(value, unit)),
				}
			)
		day["cells"] = cells
	return {
		"rows": days,
		"hours": [
			{"text": "{:02d}".format(hour) if hour in HEAT_LABELS else ""}
			for hour in range(HOURS_PER_DAY)
		],
		"low": "{:.0f} {}".format(low, unit) if values else EM_DASH,
		"high": "{:.0f} {}".format(high, unit) if values else EM_DASH,
		"scale": [{"color": color} for color in HEAT],
	}


def isIntakePump(
	row,  # type: Dict[str, Any]
):
	# type: (...) -> bool
	"""Whether an assets/status row is one of the pumps the intake measure sums."""
	area, kind, _ = MEASURES["intake"]
	return row["area"] == area and row["kind"] == kind


def gauges(
	rows,  # type: List[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Return the three gauges: availability, intake flow against capacity, reservoir level."""
	total = len(rows)
	online = sum(1 for row in rows if row["online"])
	pumps = [row for row in rows if isIntakePump(row)]
	flow = sum(row["value"] or 0.0 for row in pumps if row["online"])
	capacity = sum(row["capacity"] or 0.0 for row in pumps)
	level = [row for row in rows if (row["area"], row["kind"]) == MEASURES["reservoir"][:2]]
	reservoir = level[0]["value"] if level and level[0]["value"] is not None else 0.0
	return {
		"availability": {
			"value": round(100.0 * online / total, 1) if total else 0.0,
			"caption": "{} of {} assets online".format(online, total),
		},
		"intake": {
			"value": round(flow, 1),
			"max": capacity or 100.0,
			# joined, not formatted: without a capacity the percentage is a unicode dash
			"caption": "{:.0f} of {:.0f} L/s rated, ".format(flow, capacity)
			+ percent(flow / capacity if capacity else None),
		},
		"reservoir": {
			"value": round(reservoir, 1),
			"caption": "Latest reading",
		},
	}


def utilisation(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Return each area's load: the mean share of rated capacity its assets run at.

	An offline asset counts as zero, so a tripped pump pulls its area down.
	"""
	areas = {}  # type: Dict[str, List[Dict[str, Any]]]
	for row in rows:
		areas.setdefault(row["area"] or "Unassigned", []).append(row)
	result = []
	for name in sorted(areas, key=areaOrder):
		assets = areas[name]
		shares = [
			min((row["value"] or 0.0) / row["capacity"], 1.0)
			if row["online"] and row["capacity"]
			else 0.0
			for row in assets
		]
		load = 100.0 * sum(shares) / len(shares)
		online = sum(1 for row in assets if row["online"])
		result.append(
			{
				"area": name,
				"color": areaColor(name),
				"value": round(load, 1),
				"text": "{:.0f}%".format(load),
				"caption": "{} of {} online".format(online, len(assets)),
			}
		)
	return result


def analytics(
	statusRows,  # type: List[Dict[str, Any]]
	hourlyRows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Return everything the Analytics page shows."""
	points = hourly(hourlyRows)
	return {
		"gauges": gauges(statusRows),
		"output": output(points),
		"chart": chart(points),
		"heatmap": heatmap(points),
		"areas": utilisation(statusRows),
	}


def getAnalytics():
	# type: (...) -> Dict[str, Any]
	"""Query the assets' status and hourly readings and shape them for the Analytics page."""
	return analytics(getStatus(), toRows(namedQuery("readings/hourly")))


# the tanks whose level history the Analytics page charts, from the demo SQL historian
LEVELS = (
	("Well", "[default]Assets/North/Intake well level/value"),
	("Reservoir", "[default]Assets/East/Reservoir level/value"),
)
HISTORY_MINUTES = 60
HISTORY_POINTS = 120


def getLevelHistory():
	# type: (...) -> List[Dict[str, Any]]
	"""Query the last hour of the tanks' level history, averaged into HISTORY_POINTS points."""
	end = now()
	names = [name for name, _ in LEVELS]
	paths = [path for _, path in LEVELS]
	return averages(paths, names, addMinutes(end, -HISTORY_MINUTES), end, HISTORY_POINTS)
