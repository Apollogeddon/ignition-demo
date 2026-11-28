"""Shape asset data for the Plant page's process schematic and its equipment popup.

The schematic has a fixed place (a slot) for each piece of equipment, from the
intake well to the transfer pumps. plant() fills the slots from assets/status
rows: each symbol's state, its labels and each pipe's colour, so the view only
binds to them. equipment() shapes one asset for the popup the symbols open.
"""

import time

from library.data import toRows
from library.db import namedQuery
from library.format import EM_DASH, duration, percent
from project.assets import getStatus, reading, status
from project.events import LABELS
from project.process import MOTORS, basePath

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List, Optional

# each asset's slot in the schematic, by name, and the stage it belongs to
SLOTS = {
	"Intake well level": ("well", "well"),
	"Intake pump 1": ("intake1", "intake"),
	"Intake pump 2": ("intake2", "intake"),
	"Intake pump 3": ("intake3", "intake"),
	"Blower 1": ("blower1", "air"),
	"Blower 2": ("blower2", "air"),
	"Mixer": ("mixer", "treatment"),
	"Dosing pump": ("dosing", "dosing"),
	"Reservoir level": ("reservoir", "storage"),
	"Transfer pump 1": ("transfer1", "transfer"),
	"Transfer pump 2": ("transfer2", "transfer"),
}

# the pipes' colours: water while its stage flows, air while a blower runs, else idle
WATER = "#38BDF8"
AIR = "#A5B4FC"
DOSE = "#34D399"
IDLE = "#CBD5E1"


# the popup's trend covers the day up to the newest reading: the seeded
# 15-minute readings and the process timer's live ones
TREND_MS = 24 * 3600 * 1000
# share of the rated capacity above which the gauge's band turns amber
HIGH = 0.85
# below this share a tank's level is low
LOW = 0.15
AMBER = "#F59E0B"
TRACK = "#E2E8F0"
# the gauge bands' width, and how far outside the scale (a share of it) they start
BAND = 8
OUTSIDE = 0.01


def symbolState(
	row,  # type: Dict[str, Any]
):
	# type: (...) -> str
	"""Return a Perspective symbol state: faulted offline, running with a reading."""
	if row["kind"] not in MOTORS:
		return "default"
	if not row["online"]:
		return "faulted"
	return "running" if (row["value"] or 0) > 0 else "stopped"


def stateLabel(
	state,  # type: str
):
	# type: (...) -> str
	"""Name a symbol state for people: "Running", "Stopped", "Fault" or ""."""
	return {"running": "Running", "stopped": "Stopped", "faulted": "Fault"}.get(state, "")


def share(
	value,  # type: Optional[float]
	capacity,  # type: Optional[float]
):
	# type: (...) -> float
	"""Return value as a 0-1 share of capacity, clamped; 0 without either."""
	if not value or not capacity:
		return 0.0
	return min(max(float(value) / capacity, 0.0), 1.0)


def slot(
	row,  # type: Dict[str, Any]
):
	# type: (...) -> Dict[str, Any]
	"""Return what a schematic symbol or tank shows for one assets/status row."""
	state = symbolState(row)
	unit = row["unit"] or ""
	return {
		"id": row["id"],
		"name": row["name"],
		"path": basePath(row),
		"state": state,
		"running": state == "running",
		"status": stateLabel(state) or status(row["online"]),
		"value": row["value"] or 0.0,
		"capacity": row["capacity"] or 100.0,
		"unit": unit,
		"reading": reading(row["value"], unit),
	}


def emptySlot(
	name,  # type: str
):
	# type: (...) -> Dict[str, Any]
	"""Return a slot with no asset behind it: drawn stopped, reading a dash."""
	return {
		"id": None,
		"name": name,
		"path": "",
		"state": "stopped",
		"running": False,
		"status": "No data",
		"value": 0.0,
		"capacity": 100.0,
		"unit": "",
		"reading": EM_DASH,
	}


def stage(
	slots,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Sum a stage's running equipment: its flow, and how many of how many run.

	The flow takes the unit of the stage's first slot, so it stays unicode on Jython.
	"""
	slots = list(slots)
	unit = slots[0]["unit"] if slots else ""
	running = [item for item in slots if item["running"]]
	total = sum(item["value"] for item in running)
	return {
		"flow": total,
		"reading": reading(total, unit),
		"running": len(running),
		"count": len(slots),
		"caption": "{} of {} running".format(len(running), len(slots)),
	}


def plant(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> Dict[str, Any]
	"""Return the schematic's slots, its stage KPIs and its pipes' colours."""
	slots = {}  # type: Dict[str, Dict[str, Any]]
	stages = {}  # type: Dict[str, List[Dict[str, Any]]]
	for row in rows:
		place = SLOTS.get(row["name"])
		if place is None:
			continue
		item = slot(row)
		slots[place[0]] = item
		stages.setdefault(place[1], []).append(item)
	for name, (key, _) in SLOTS.items():
		if key not in slots:
			slots[key] = emptySlot(name)

	intake = stage(stages.get("intake", []))
	air = stage(stages.get("air", []))
	transfer = stage(stages.get("transfer", []))
	dosing = slots["dosing"]["running"]
	flowing = intake["running"] > 0
	return {
		"slots": slots,
		"kpis": {
			"intake": intake,
			"air": air,
			"transfer": transfer,
			"reservoir": slots["reservoir"]["reading"],
			"reservoirCaption": "Well " + slots["well"]["reading"],
		},
		"valve": "open" if flowing else "closed",
		"pipes": {
			"intake": WATER if flowing else IDLE,
			"air": AIR if air["running"] else IDLE,
			"dosing": DOSE if dosing else IDLE,
			"transfer": WATER if transfer["running"] else IDLE,
		},
	}


def getPlant():
	# type: (...) -> Dict[str, Any]
	"""Query the assets' status and shape it for the Plant page."""
	return plant(getStatus())


def gauge(
	value,  # type: Optional[float]
	capacity,  # type: float
	kind,  # type: str
):
	# type: (...) -> Dict[str, Any]
	"""Return the popup gauge's value, scale and bands: amber when high, and low for tanks.

	The gauge draws a line from its centre where each band starts, so every band
	starts just below the scale, and later bands cover earlier ones: amber to the
	top, then the grey track up to the high mark.
	"""
	below = -capacity * OUTSIDE
	ranges = [
		{"start": below, "end": capacity, "color": AMBER, "width": BAND},
		{"start": below, "end": capacity * HIGH, "color": TRACK, "width": BAND},
	]
	if kind == "level":
		ranges.append({"start": below, "end": capacity * LOW, "color": AMBER, "width": BAND})
	return {"value": value or 0.0, "max": capacity, "ranges": ranges}


def trend(
	readings,  # type: Iterable[Dict[str, Any]]
	unit,  # type: str
):
	# type: (...) -> Dict[str, Any]
	"""Return the last day of readings as sparkline points, with their low, mean and high."""
	readings = list(readings)
	newest = readings[-1]["time"] if readings else 0
	values = [row["value"] for row in readings if row["time"] > newest - TREND_MS]
	if not values:
		return {"points": [], "low": EM_DASH, "mean": EM_DASH, "high": EM_DASH}
	return {
		"points": values,
		"low": reading(min(values), unit),
		"mean": reading(sum(values) / len(values), unit),
		"high": reading(max(values), unit),
	}


def lastEvent(
	events,  # type: List[Dict[str, Any]]
	nowMs,  # type: float
):
	# type: (...) -> str
	"""Describe the newest event, e.g. "Acknowledged 2h 05m ago by operator"."""
	if not events:
		return "No events recorded"
	event = events[0]
	text = (LABELS.get(event["kind"]) or event["kind"]) + " "
	text += duration((nowMs - event["time"]) / 1000.0) + " ago"
	if event["operator"]:
		# joined, not formatted: the operator is unicode on Jython 2.7
		text += " by " + event["operator"]
	return text


def equipment(
	assetId,  # type: Any
	rows,  # type: Iterable[Dict[str, Any]]
	readings,  # type: Iterable[Dict[str, Any]]
	events,  # type: List[Dict[str, Any]]
	nowMs,  # type: float
):
	# type: (...) -> Dict[str, Any]
	"""Return what the equipment popup shows for one asset, or that it was not found."""
	found = [row for row in rows if row["id"] == assetId]
	if not found:
		return {"found": False, "name": "Equipment not found", "trend": trend([], "")}
	row = found[0]
	unit = row["unit"] or ""
	capacity = row["capacity"] or 100.0
	item = slot(row)
	return {
		"found": True,
		"id": row["id"],
		"name": row["name"],
		"subtitle": (row["area"] or "Unassigned") + " area, " + (row["kind"] or "").capitalize(),
		"online": bool(row["online"]),
		"status": item["status"],
		"pill": "Pill/Base Pill/Ok"
		if item["state"] in ("running", "default")
		else "Pill/Base Pill/Bad",
		"unit": unit,
		"reading": item["reading"],
		"motor": row["kind"] in MOTORS,
		"rated": "Rated " + reading(capacity, unit),
		"load": percent(share(row["value"], capacity)) + " of rated",
		"gauge": gauge(row["value"], capacity, row["kind"]),
		"trend": trend(readings, unit),
		"lastEvent": lastEvent(events, nowMs),
	}


def getEquipment(
	assetId,  # type: Any
):
	# type: (...) -> Dict[str, Any]
	"""Query one asset's status, readings and newest event for the equipment popup."""
	try:
		assetId = int(assetId)
	except (TypeError, ValueError):
		return equipment(None, [], [], [], 0)
	readings = toRows(namedQuery("readings/asset", {"assetId": assetId}))
	events = toRows(namedQuery("events/list", {"assetId": assetId, "limit": 1}))
	return equipment(assetId, getStatus(), readings, events, time.time() * 1000)


def openEquipment(
	assetId,  # type: Any
	name,  # type: str
	path="",  # type: str
):
	# type: (...) -> None
	"""Open the equipment popup for a schematic slot; a slot with no asset opens none.

	path is the asset's UDT instance, which the popup binds its live reading,
	state and Start/Stop to.
	"""
	if assetId is None:
		return
	from system.perspective import openPopup

	openPopup(
		"equipment",
		"Popup/Equipment",
		params={"assetId": assetId, "tagPath": path},
		title=name,
		showCloseIcon=True,
		draggable=True,
		resizable=False,
		modal=True,
		overlayDismiss=True,
	)
