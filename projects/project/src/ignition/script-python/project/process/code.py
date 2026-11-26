"""A small water plant model that drives the assets' tags, so every view shows a live process.

The project's gateway timer event (ignition/timer/process) calls tick() every
TICK_SECONDS. tick() reads each asset's UDT instance, steps the model, writes
the results back and records each trip, reset, start and stop as a status
event. Every LOG_MINUTES it appends each asset's reading to asset_reading, so
the charts built on the seeded 72 hours keep growing.

step() is the model, and pure:
- the intake pumps draw from the well, harder the fuller it is, while the
  river refills it;
- the treated water reaches the reservoir through the outlet valve, which
  throttles as the reservoir fills;
- the transfer pumps follow the network's daily demand;
- a running motor trips now and then (Motor Fault alarm) and is back in service
  RESET_SECONDS later, unless an operator starts it sooner.

An operator starts or stops a motor by writing its motor/cmdRun tag (the
Plant page's equipment popup does).
"""

import math
import random
import time
import traceback

from java.lang import Throwable
from library.data import toRows
from library.db import namedQuery, namedUpdate
from system.perspective import getSessionInfo, sendMessage
from system.tag import readBlocking, writeBlocking
from system.util import getGlobals, getLogger

LOGGER = getLogger("demo.project.process")

PROJECT = "project"
PROVIDER = "default"
TICK_SECONDS = 5.0
# how often every asset's reading is appended to asset_reading
LOG_MINUTES = 5
# how long the asset list is cached between database reads
ASSETS_SECONDS = 300
# each reading's noise comes from the model's own generator, not a security one
RNG = random.Random()  # noqa: S311

# each asset's part in the process, by its area and kind
ROLES = {
	("North", "level"): "well",
	("North", "pump"): "intake",
	("South", "pump"): "dosing",
	("South", "blower"): "blower",
	("South", "mixer"): "mixer",
	("East", "level"): "reservoir",
	("East", "pump"): "transfer",
}
MOTORS = ("pump", "blower", "mixer")

# the river's inflow to the well, L/s: a mean and a slow swing
RIVER_MEAN = 78.0
RIVER_SWING = 8.0
RIVER_PERIOD_SECONDS = 3 * 3600
# litres per percent of each tank
WELL_LITRES = 3000.0
RESERVOIR_LITRES = 10000.0
# an intake pump's share of its rated flow: BASE plus HEAD per percent of well level
INTAKE_BASE = 0.45
INTAKE_HEAD = 0.0035
# the outlet valve is fully open below OPEN_BELOW and shut at CLOSED_AT (reservoir %)
VALVE_OPEN_BELOW = 80.0
VALVE_CLOSED_AT = 95.0
# the dosing pump's flow as a share of the treated flow
DOSE_SHARE = 0.02
# a running blower's share of its rated air flow, and its discharge pressure (kPa)
BLOWER_SHARE = 0.69
BLOWER_KPA = 48.0
MIXER_RPM = 55.0
# relative noise on every reading
NOISE = 0.015
# a running motor's mean time between faults, and how long a trip lasts
MTBF_SECONDS = 4 * 3600.0
RESET_SECONDS = 15 * 60.0

MESSAGES = {
	"trip": "Tripped: motor fault",
	"reset": "Back in service after maintenance",
	"start": "Started",
	"stop": "Stopped",
}

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List, Optional, Tuple

	Values = Dict[str, Dict[str, Any]]


def clamp(
	value,  # type: float
	low,  # type: float
	high,  # type: float
):
	# type: (...) -> float
	"""Limit value to low..high."""
	return max(low, min(high, value))


def demand(
	nowS,  # type: float
):
	# type: (...) -> float
	"""Return the network's demand, a share of a transfer pump's rated flow.

	It peaks in the morning and the evening.
	"""
	hour = (nowS % 86400) / 3600.0
	return (
		0.72
		+ 0.14 * math.sin(2 * math.pi * (hour - 9) / 24)
		+ 0.08 * math.sin(4 * math.pi * (hour - 7) / 24)
	)


def river(
	nowS,  # type: float
):
	# type: (...) -> float
	"""Return the river's inflow to the intake well, L/s."""
	return RIVER_MEAN + RIVER_SWING * math.sin(2 * math.pi * nowS / RIVER_PERIOD_SECONDS)


def valveOpening(
	reservoir,  # type: float
):
	# type: (...) -> float
	"""Return the outlet valve's opening, 0 to 1: it throttles as the reservoir fills."""
	return clamp((VALVE_CLOSED_AT - reservoir) / (VALVE_CLOSED_AT - VALVE_OPEN_BELOW), 0.0, 1.0)


def role(
	asset,  # type: Dict[str, Any]
):
	# type: (...) -> Optional[str]
	"""Return an asset's part in the process, or None when the model has none for it."""
	return ROLES.get((asset["area"], asset["kind"]))


def motor(
	value,  # type: Dict[str, Any]
	started,  # type: Optional[float]
	nowS,  # type: float
	rng,  # type: Any
):
	# type: (...) -> Tuple[bool, bool, Optional[float], Optional[str]]
	"""Step one motor; return (running, fault, trip time, transition or None).

	A fault with no trip time (set by the startup sync, or an operator's reset
	in progress) counts from now. A trip clears RESET_SECONDS after it started,
	or when an operator restarts the motor (its popup writes fault false). A
	trip and a reset are their own transitions, not also a stop or a start.
	"""
	wasRunning = bool(value.get("running"))
	fault = bool(value.get("fault"))
	change = None  # type: Optional[str]
	if fault:
		started = nowS if started is None else started
		if nowS - started >= RESET_SECONDS:
			fault, started, change = False, None, "reset"
	elif wasRunning and rng.random() < TICK_SECONDS / MTBF_SECONDS:
		fault, started, change = True, nowS, "trip"
	else:
		started = None
	run = bool(value.get("cmdRun", True)) and not fault
	if change is None and run != wasRunning and not fault:
		change = "start" if run else "stop"
	return run, fault, started, change


def flows(
	byRole,  # type: Dict[str, List[Dict[str, Any]]]
	running,  # type: Dict[str, bool]
	levels,  # type: Tuple[float, float]
	nowS,  # type: float
	noisy,  # type: Any
):
	# type: (...) -> Tuple[Values, float, float, float]
	"""Return each pump's flow, with the intake, treated and transfer totals (L/s)."""
	well, reservoir = levels
	out = {}  # type: Values
	totals = {"intake": 0.0, "transfer": 0.0}
	share = {"intake": INTAKE_BASE + INTAKE_HEAD * well, "transfer": demand(nowS)}
	for part in ("intake", "transfer"):
		for asset in byRole.get(part, []):
			on = running.get(asset["name"])
			flow = noisy(asset["capacity"] * share[part]) if on else 0.0
			out[asset["name"]] = {"value": flow}
			totals[part] += flow
	treated = totals["intake"] * valveOpening(reservoir)
	return out, totals["intake"], treated, totals["transfer"]


def treatment(
	byRole,  # type: Dict[str, List[Dict[str, Any]]]
	running,  # type: Dict[str, bool]
	treated,  # type: float
	noisy,  # type: Any
):
	# type: (...) -> Values
	"""Return the dosing pump's, the blowers' and the mixer's readings."""
	out = {}  # type: Values
	for asset in byRole.get("dosing", []):
		on = running.get(asset["name"])
		dose = min(asset["capacity"], DOSE_SHARE * treated) if on else 0.0
		out[asset["name"]] = {"value": noisy(dose)}
	for asset in byRole.get("blower", []):
		on = running.get(asset["name"])
		out[asset["name"]] = {
			"value": noisy(asset["capacity"] * BLOWER_SHARE) if on else 0.0,
			"pressure": noisy(BLOWER_KPA) if on else 0.0,
		}
	for asset in byRole.get("mixer", []):
		on = running.get(asset["name"])
		out[asset["name"]] = {"value": noisy(MIXER_RPM) if on else 0.0}
	return out


def step(
	assets,  # type: List[Dict[str, Any]]
	values,  # type: Values
	nowS,  # type: float
	rng,  # type: Any
	tripped,  # type: Dict[str, float]
):
	# type: (...) -> Tuple[Values, Dict[str, float], List[Tuple[str, str]]]
	"""Advance the plant by one tick (TICK_SECONDS).

	values holds each asset's tags by name: value, and for a motor running,
	fault and cmdRun. Returns the new values (a motor's also speed, % of rated),
	the trip times to carry to the next step, and the transitions as
	(asset name, "trip" | "reset" | "start" | "stop").
	"""
	running = {}  # type: Dict[str, bool]
	faults = {}  # type: Dict[str, bool]
	since = {}  # type: Dict[str, float]
	changes = []  # type: List[Tuple[str, str]]
	byRole = {}  # type: Dict[str, List[Dict[str, Any]]]
	for asset in assets:
		name = asset["name"]
		byRole.setdefault(role(asset) or "", []).append(asset)
		if asset["kind"] not in MOTORS:
			continue
		run, fault, started, change = motor(values.get(name, {}), tripped.get(name), nowS, rng)
		running[name], faults[name] = run, fault
		if started is not None:
			since[name] = started
		if change:
			changes.append((name, change))

	def noisy(value):
		# type: (float) -> float
		return max(0.0, value * (1 + rng.gauss(0, NOISE)))

	def level(part):
		# type: (str) -> float
		items = byRole.get(part) or [{"name": ""}]
		return float(values.get(items[0]["name"], {}).get("value") or 0.0)

	well, reservoir = level("well"), level("reservoir")
	out, intake, treated, transfer = flows(byRole, running, (well, reservoir), nowS, noisy)
	out.update(treatment(byRole, running, treated, noisy))
	for asset in byRole.get("well", []):
		change = (river(nowS) - intake) * TICK_SECONDS / WELL_LITRES
		out[asset["name"]] = {"value": clamp(well + change, 0, 100)}
	for asset in byRole.get("reservoir", []):
		change = (treated - transfer) * TICK_SECONDS / RESERVOIR_LITRES
		out[asset["name"]] = {"value": clamp(reservoir + change, 0, 100)}
	capacity = {asset["name"]: asset["capacity"] or 1.0 for asset in assets}
	for name, run in running.items():
		item = out.setdefault(name, {"value": 0.0})
		item["running"], item["fault"] = run, faults[name]
		item["speed"] = clamp(100.0 * item["value"] / capacity[name], 0, 100)
	return out, since, changes


def initial(
	assets,  # type: List[Dict[str, Any]]
	values,  # type: Values
):
	# type: (...) -> Values
	"""Return the values to start from when the tags are fresh.

	A tank whose tag reads zero starts at its latest reading in the database,
	an asset the database has offline starts tripped, and every motor starts
	in the state its command gives, so a new gateway picks up where the seeded
	history ends without recording a start for each motor.
	"""
	start = {}  # type: Values
	for asset in assets:
		value = dict(values.get(asset["name"], {}))
		if asset["kind"] == "level" and not value.get("value"):
			value["value"] = asset.get("value") or 0.0
		if asset["kind"] in MOTORS:
			if not asset.get("online", True):
				value["fault"] = True
			# already in the state its command and fault give, so the first step records nothing
			value["running"] = bool(value.get("cmdRun", True)) and not value.get("fault")
		start[asset["name"]] = value
	return start


def basePath(
	asset,  # type: Dict[str, Any]
	provider=PROVIDER,  # type: str
):
	# type: (...) -> str
	"""Return an asset's UDT instance path, e.g. [default]Assets/North/Intake pump 1."""
	return "[" + provider + "]Assets/" + (asset["area"] or "Unassigned") + "/" + asset["name"]


def members(
	asset,  # type: Dict[str, Any]
):
	# type: (...) -> List[Tuple[str, str]]
	"""Return the (key, member path) pairs tick() reads and writes for an asset."""
	pairs = [("value", "value")]
	if asset["kind"] in MOTORS:
		pairs += [
			("running", "motor/running"),
			("fault", "motor/fault"),
			("cmdRun", "motor/cmdRun"),
			("speed", "motor/speed"),
		]
	if asset["kind"] == "blower":
		pairs.append(("pressure", "pressure"))
	return pairs


def readValues(
	assets,  # type: List[Dict[str, Any]]
):
	# type: (...) -> Values
	"""Read every asset's members in one call."""
	paths = []  # type: List[str]
	keys = []  # type: List[Tuple[str, str]]
	for asset in assets:
		for key, member in members(asset):
			paths.append(basePath(asset) + "/" + member)
			keys.append((asset["name"], key))
	values = {}  # type: Values
	for (name, key), qv in zip(keys, readBlocking(paths)):
		values.setdefault(name, {})[key] = qv.value
	return values


def writeValues(
	assets,  # type: List[Dict[str, Any]]
	values,  # type: Values
):
	# type: (...) -> None
	"""Write the model's outputs (never cmdRun, which is the operator's) in one call."""
	paths = []  # type: List[str]
	written = []  # type: List[Any]
	for asset in assets:
		value = values.get(asset["name"], {})
		for key, member in members(asset):
			if key != "cmdRun" and key in value:
				paths.append(basePath(asset) + "/" + member)
				written.append(value[key])
	writeBlocking(paths, written)


def dueToLog(
	nowS,  # type: float
	lastSlot,  # type: Optional[int]
):
	# type: (...) -> Tuple[bool, int]
	"""Whether the readings are due in this LOG_MINUTES slot; returns it with the slot."""
	current = int(nowS // (LOG_MINUTES * 60))
	return current != lastSlot, current


def logReadings(
	assets,  # type: List[Dict[str, Any]]
	values,  # type: Values
):
	# type: (...) -> None
	"""Append every asset's reading to asset_reading."""
	for asset in assets:
		value = values.get(asset["name"], {}).get("value")
		if value is not None:
			namedUpdate("readings/insert", {"assetId": asset["id"], "value": float(value)})


def recordChanges(
	assets,  # type: List[Dict[str, Any]]
	changes,  # type: List[Tuple[str, str]]
):
	# type: (...) -> int
	"""Record each transition as a status event; return how many were recorded."""
	ids = {asset["name"]: asset["id"] for asset in assets}
	for name, change in changes:
		namedQuery(
			"events/insert",
			{
				"assetId": ids[name],
				"kind": "status",
				"message": MESSAGES[change],
				"operator": "Process",
			},
		)
		LOGGER.info("{}: {}".format(name, MESSAGES[change]))
	return len(changes)


def notifySessions():
	# type: (...) -> None
	"""Tell the project's open sessions an event was recorded (the eventRecorded message)."""
	for session in getSessionInfo(projectFilter=PROJECT):
		# the adapter exposes the JSON keys as attributes (__findattr_ex__)
		sessionId = str(getattr(session, "id"))  # noqa: B009 - the stubs declare no id attribute
		try:
			sendMessage("eventRecorded", {}, scope="session", sessionId=sessionId)
		except (Exception, Throwable):  # noqa: BLE001 - a closing session mustn't stop the rest
			LOGGER.debug("eventRecorded not sent to {}".format(sessionId))


def command(
	path,  # type: str
	run,  # type: bool
):
	# type: (...) -> Dict[str, Any]
	"""Start or stop a motor for an operator: write its motor/cmdRun; return {ok, text}.

	Starting also clears a trip, as an operator's reset. The process timer
	applies the command at its next tick and records the start or stop.
	"""
	paths = [path + "/motor/cmdRun"]
	values = [run]  # type: List[Any]
	if run:
		paths.append(path + "/motor/fault")
		values.append(False)
	try:
		results = writeBlocking(paths, values)
	except (Exception, Throwable) as e:  # noqa: BLE001 - shown to the operator instead
		LOGGER.warn("Command to {} failed: {}".format(path, e))
		return {"ok": False, "text": "The command was not written; try again"}
	if not all(result.isGood() for result in results):
		return {"ok": False, "text": "The command was not written; try again"}
	return {"ok": True, "text": "Starting" if run else "Stopping"}


def state():
	# type: (...) -> Dict[str, Any]
	"""Return the model's state between ticks, kept in the gateway's globals."""
	return getGlobals().setdefault("demo.process", {"tripped": {}, "logSlot": None})


def loadAssets(
	memory,  # type: Dict[str, Any]
	nowS,  # type: float
):
	# type: (...) -> List[Dict[str, Any]]
	"""Return the enabled assets the model drives, cached for ASSETS_SECONDS.

	assets/status gives each one's capacity, and the online flag and latest
	reading initial() starts fresh tags from.
	"""
	if memory.get("assets") is None or nowS - memory.get("assetsAt", 0) > ASSETS_SECONDS:
		rows = toRows(namedQuery("assets/status"))
		memory["assets"] = [row for row in rows if role(row)]
		memory["assetsAt"] = nowS
	return memory["assets"]


def tick(
	nowS=None,  # type: Optional[float]
):
	# type: (...) -> None
	"""Step the plant once: read the tags, step the model, write them back, record changes."""
	nowS = time.time() if nowS is None else nowS
	memory = state()
	try:
		assets = loadAssets(memory, nowS)
		values = readValues(assets)
		if not memory.get("started"):
			values = initial(assets, values)
			memory["started"] = True
		out, memory["tripped"], changes = step(assets, values, nowS, RNG, memory["tripped"])
		writeValues(assets, out)
		if recordChanges(assets, changes):
			notifySessions()
		due, memory["logSlot"] = dueToLog(nowS, memory["logSlot"])
		if due:
			logReadings(assets, out)
	except (Exception, Throwable) as e:  # noqa: BLE001 - the next tick tries again
		LOGGER.warn("Process tick failed: {}".format(e))
		LOGGER.debug(traceback.format_exc())
