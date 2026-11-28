"""Count the assets' alarms for the Alarms page and the header.

The alarms themselves are configured on the UDTs (library/src/udts): a motor
fault, and a tank's high and low level. Perspective's Alarm Status Table and
Alarm Journal Table show and acknowledge them; this module only counts.
"""

import traceback

from java.lang import Throwable
from system.alarm import queryStatus
from system.util import getLogger

LOGGER = getLogger("demo.project.alarms")

# the asset instances' alarms, wherever they are
SOURCE = "*Assets/*"
ACTIVE = ("ActiveUnacked", "ActiveAcked")
UNACKED = ("ActiveUnacked", "ClearUnacked")
HIGH = ("High", "Critical")

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable


def enumName(
	value,  # type: Any
):
	# type: (...) -> str
	"""Return a Java enum's name (ActiveUnacked), not its display text (Active, Unacknowledged)."""
	name = getattr(value, "name", None)
	return str(name() if callable(name) else value)


def counts(
	events,  # type: Iterable[Any]
):
	# type: (...) -> Dict[str, int]
	"""Count alarm events: active, unacknowledged, and active at High or Critical priority."""
	result = {"active": 0, "unacked": 0, "high": 0}
	for event in events:
		state = enumName(event.getState())
		active = state in ACTIVE
		result["active"] += active
		result["unacked"] += state in UNACKED
		result["high"] += active and enumName(event.getPriority()) in HIGH
	return result


def getCounts():
	# type: (...) -> Dict[str, int]
	"""Query the assets' alarms that are active or unacknowledged, and count them."""
	try:
		events = queryStatus(source=[SOURCE], state=list(set(ACTIVE + UNACKED)))
	except (Exception, Throwable) as e:  # noqa: BLE001 - the header still shows the link
		LOGGER.warn("Alarm status not queried: {}".format(e))
		LOGGER.debug(traceback.format_exc())
		return {"active": 0, "unacked": 0, "high": 0}
	return counts(events)
