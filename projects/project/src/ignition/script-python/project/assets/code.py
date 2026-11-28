"""Asset queries and summaries for the overview views."""

from java.lang import Throwable
from library.data import toRows
from library.db import namedQuery
from library.format import EM_DASH
from project.events import tableRows as eventRows
from project.process import MOTORS, readValues, role
from system.tag import configure
from system.util import getLogger

LOGGER = getLogger("demo.project.assets")

# a reading at or above 100 shows without decimals (air flow, rpm), below with one
WHOLE_NUMBER_FROM = 100

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List, Optional


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
	summary = summarise(toRows(namedQuery("assets/list")))
	LOGGER.debug("Summarised {} areas".format(len(summary)))
	return summary


def live(
	rows,  # type: List[Dict[str, Any]]
	values,  # type: Dict[str, Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Overlay each asset's tags on its assets/status row.

	value becomes the tag's live reading, and a motor is online unless its
	motor/fault is set; running says whether it runs. A tag that reads nothing
	(no instance yet, or bad quality) keeps the database's value.
	"""
	result = []
	for source in rows:
		row = dict(source)
		tags = values.get(row["name"]) or {}
		# a tag that reads nothing (no instance yet, or bad quality) leaves the row's value
		if tags.get("value") is not None:
			row["value"] = tags["value"]
		if row["kind"] in MOTORS and tags.get("fault") is not None:
			row["online"] = not tags["fault"]
			row["running"] = bool(tags.get("running"))
		result.append(row)
	return result


def getStatus():
	# type: (...) -> List[Dict[str, Any]]
	"""Return every enabled asset with its live reading (its tags) and latest event.

	The rows come from assets/status, with the tags overlaid; if the tags can't
	be read, the database's latest reading and online flag stand.
	"""
	rows = toRows(namedQuery("assets/status"))
	try:
		return live(rows, readValues([row for row in rows if role(row)]))
	except (Exception, Throwable) as e:  # noqa: BLE001 - the database's values still show
		LOGGER.warn("Asset tags not read; showing the database's readings: {}".format(e))
		return rows


def reading(
	value,  # type: Optional[float]
	unit,  # type: str
):
	# type: (...) -> str
	"""Format a reading with its unit, e.g. "42.3 L/s" or "1,450 rpm".

	Joined by concatenation: the unit is unicode on Jython 2.7, and str.format
	would encode it as ASCII.
	"""
	if value is None:
		return EM_DASH
	pattern = "{:,.0f}" if abs(value) >= WHOLE_NUMBER_FROM else "{:.1f}"
	text = pattern.format(value)
	return (text + " " + unit).strip()


def status(
	online,  # type: Any
):
	# type: (...) -> str
	"""Return "Online" or "Offline"; tables show it as a pill (the Cells/Pill view)."""
	return "Online" if online else "Offline"


def tableRows(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Shape assets/status rows for an asset table: status and formatted readings."""
	return [
		{
			"id": row["id"],
			"name": row["name"],
			"area": row["area"] or "Unassigned",
			"kind": (row["kind"] or "").capitalize(),
			"status": status(row["online"]),
			"reading": reading(row["value"], row["unit"] or ""),
			"event": row["event_ms"],
		}
		for row in rows
	]


def getTable():
	# type: (...) -> List[Dict[str, Any]]
	"""Return every enabled asset as rows for the Assets page's table."""
	return tableRows(getStatus())


def detail(
	assetId,  # type: Any
	rows,  # type: Iterable[Dict[str, Any]]
	readings,  # type: Iterable[Dict[str, Any]]
	events,  # type: List[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Return what the asset detail panel shows for one asset, or an empty panel.

	readings become the time series chart's data ({time, value}); events are
	the asset's latest, newest first, as events/list returns them.
	"""
	found = [row for row in rows if row["id"] == assetId]
	if not found:
		return {"found": False, "name": "No asset selected", "readings": [], "events": []}
	row = found[0]
	unit = row["unit"] or ""
	return {
		"found": True,
		"id": row["id"],
		"name": row["name"],
		"area": row["area"] or "Unassigned",
		"kind": (row["kind"] or "").capitalize(),
		"online": bool(row["online"]),
		"status": status(row["online"]),
		"unit": unit,
		"reading": reading(row["value"], unit),
		"readings": [{"time": r["time"], "value": r["value"]} for r in readings],
		"events": events,
	}


def getDetail(
	assetId,  # type: Any
):
	# type: (...) -> Dict[str, Any]
	"""Query one asset's status, readings and latest events for the detail panel."""
	try:
		assetId = int(assetId)
	except (TypeError, ValueError):
		return detail(None, [], [], [])
	readings = toRows(namedQuery("readings/asset", {"assetId": assetId}))
	events = eventRows(toRows(namedQuery("events/list", {"assetId": assetId, "limit": 5})))
	return detail(assetId, getStatus(), readings, events)


def buildInstances(
	rows,  # type: Iterable[Dict[str, Any]]
	kinds,  # type: Iterable[str]
):
	# type: (...) -> Dict[str, List[Dict[str, Any]]]
	"""Group one UDT instance per asset by area folder.

	An asset's kind names its UDT, equipment/<kind>. Assets whose kind has no
	definition are skipped and logged, so one bad row does not stop the rest.
	"""
	known = set(kinds)
	folders = {}  # type: Dict[str, List[Dict[str, Any]]]
	for row in rows:
		if row["kind"] not in known:
			LOGGER.warn(
				"Asset {} has kind {} with no UDT; skipped".format(row["name"], row["kind"])
			)
			continue
		folder = row["area"] or "Unassigned"
		folders.setdefault(folder, []).append(
			{
				"name": row["name"],
				"tagType": "UdtInstance",
				"typeId": "equipment/{}".format(row["kind"]),
			}
		)
	return folders


def syncInstances(
	provider="default",  # type: str
	kinds=("pump", "blower", "mixer", "level"),  # type: Iterable[str]
):
	# type: (...) -> int
	"""Create or update a UDT instance for every enabled asset; return how many.

	Instances are merged ("m"), so values and overrides set on existing
	instances are kept. Instances of removed assets are left for review.
	"""
	folders = buildInstances(toRows(namedQuery("assets/list")), kinds)
	for folder, tags in sorted(folders.items()):
		configure("[{}]Assets/{}".format(provider, folder), tags, "m")
	count = sum(len(tags) for tags in folders.values())
	LOGGER.info("Synchronised {} asset instances in {} areas".format(count, len(folders)))
	return count
