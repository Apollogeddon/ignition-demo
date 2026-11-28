"""Operator events: record notes and acknowledgements, and list them.

A view records an event by sending a request to the project's recordEvent
gateway message handler (send), which calls handle: it validates the payload,
writes the row through the events/insert named query and answers with a
result the view shows. The Events page lists the rows (getTable).
"""

import time
import traceback

from java.lang import Throwable
from library.data import toRows
from library.db import namedQuery
from system.util import getLogger, sendRequest

LOGGER = getLogger("demo.project.events")

PROJECT = "project"
HANDLER = "recordEvent"
TIMEOUT_SECONDS = 10

# the kinds an operator can record, and what the view says once one is
KINDS = {"acknowledge": "Acknowledgement recorded", "note": "Note recorded"}
LABELS = {"acknowledge": "Acknowledged", "note": "Note", "status": "Status"}
MAX_MESSAGE = 500
MAX_OPERATOR = 64
DEFAULT_OPERATOR = "guest"
DEFAULT_LIMIT = 200

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List, Optional


class EventError(ValueError):
	"""A request to record an event that cannot be recorded, with the reason why."""


def toInt(
	value,  # type: Any
):
	# type: (...) -> Optional[int]
	"""Return value as an int, or None when it is not a whole number."""
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def validate(
	payload,  # type: Any
):
	# type: (...) -> Dict[str, Any]
	"""Return the events/insert parameters for a request, or raise EventError.

	payload is {assetId, kind, message, operator}; a note needs a message, an
	acknowledgement does not.
	"""
	if payload is None:
		msg = "No event to record"
		raise EventError(msg)
	assetId = toInt(payload.get("assetId"))
	if assetId is None:
		msg = "Select an asset first"
		raise EventError(msg)
	kind = payload.get("kind")
	if kind not in KINDS:
		msg = "Unknown event kind"
		raise EventError(msg)
	message = (payload.get("message") or "").strip()
	if kind == "note" and not message:
		msg = "Write a note first"
		raise EventError(msg)
	if len(message) > MAX_MESSAGE:
		msg = "Keep the note under {} characters".format(MAX_MESSAGE)
		raise EventError(msg)
	operator = (payload.get("operator") or "").strip()[:MAX_OPERATOR] or DEFAULT_OPERATOR
	return {"assetId": assetId, "kind": kind, "message": message, "operator": operator}


def record(
	params,  # type: Dict[str, Any]
):
	# type: (...) -> Dict[str, Any]
	"""Insert a validated event; return its id and time (epoch milliseconds)."""
	rows = toRows(namedQuery("events/insert", params))
	if not rows:
		msg = "The database did not return the new event"
		raise EventError(msg)
	return {"id": rows[0]["id"], "time": rows[0]["time"]}


def handle(
	payload,  # type: Any
):
	# type: (...) -> Dict[str, Any]
	"""Record an event for the recordEvent message handler; never raises.

	Returns {ok: True, id, time, kind, text} or {ok: False, text}, where text
	is what the view shows the operator.
	"""
	try:
		params = validate(payload)
		row = record(params)
	except EventError as e:
		return {"ok": False, "text": e.args[0]}
	except (Exception, Throwable) as e:  # noqa: BLE001 - answer the view instead of failing
		LOGGER.error("Event not recorded: {}\n{}".format(e, traceback.format_exc()))
		return {"ok": False, "text": "The event could not be recorded; see the gateway log"}
	# no operator or message in the log line: they are unicode, which
	# str.format would encode as ASCII on Jython 2.7
	LOGGER.info("Recorded {} {} for asset {}".format(params["kind"], row["id"], params["assetId"]))
	return {
		"ok": True,
		"id": row["id"],
		"time": row["time"],
		"kind": params["kind"],
		"text": KINDS[params["kind"]],
	}


def send(
	assetId,  # type: Any
	kind,  # type: str
	message="",  # type: str
	operator=None,  # type: Optional[str]
):
	# type: (...) -> Dict[str, Any]
	"""Ask the gateway's recordEvent handler to record an event; return its answer.

	Called from a view's script. Failures to reach the handler come back as
	{ok: False, text} too, so the view always has something to show.
	"""
	payload = {"assetId": assetId, "kind": kind, "message": message, "operator": operator}
	try:
		result = sendRequest(PROJECT, HANDLER, payload, timeoutSec=TIMEOUT_SECONDS)
	except (Exception, Throwable) as e:  # noqa: BLE001 - shown to the operator instead
		LOGGER.warn("Request to {} failed: {}".format(HANDLER, e))
		return {"ok": False, "text": "The gateway did not answer; try again"}
	return dict(result) if result is not None else {"ok": False, "text": "No answer"}


def tableRows(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Shape events/list rows for a table, the kind as a label (a pill in Cells/Pill)."""
	return [
		{
			"id": row["id"],
			"time": row["time"],
			"asset": row["asset"],
			"area": row["area"],
			"kind": LABELS.get(row["kind"], row["kind"]),
			"message": row["message"],
			"operator": row["operator"],
		}
		for row in rows
	]


def counts(
	rows,  # type: Iterable[Dict[str, Any]]
	nowMs,  # type: float
):
	# type: (...) -> Dict[str, int]
	"""Count events by kind, and those of the last 24 hours."""
	result = {"total": 0, "acknowledge": 0, "note": 0, "status": 0, "day": 0}
	for row in rows:
		result["total"] += 1
		if row["kind"] in result:
			result[row["kind"]] += 1
		if nowMs - row["time"] <= 86400 * 1000:
			result["day"] += 1
	return result


def getEvents(
	assetId=0,  # type: int
	limit=DEFAULT_LIMIT,  # type: int
):
	# type: (...) -> List[Dict[str, Any]]
	"""Return the latest events, newest first: every asset's, or one asset's."""
	return toRows(namedQuery("events/list", {"assetId": assetId, "limit": limit}))


def getTable():
	# type: (...) -> Dict[str, Any]
	"""Return the Events page's table rows and counts."""
	rows = getEvents()
	return {"rows": tableRows(rows), "counts": counts(rows, time.time() * 1000)}
