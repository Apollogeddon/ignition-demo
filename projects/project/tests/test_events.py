"""Tests for project.events, behind the recordEvent gateway message handler."""

from unittest.mock import MagicMock, patch

import pytest
from project.events.code import (
	DEFAULT_OPERATOR,
	EventError,
	counts,
	getEvents,
	getTable,
	handle,
	send,
	tableRows,
	validate,
)


def test_validate_a_note() -> None:
	payload = {"assetId": "3", "kind": "note", "message": "  Bearing noise  ", "operator": "ann"}
	assert validate(payload) == {
		"assetId": 3,
		"kind": "note",
		"message": "Bearing noise",
		"operator": "ann",
	}


def test_validate_an_acknowledgement_needs_no_message_or_operator() -> None:
	params = validate({"assetId": 7, "kind": "acknowledge", "message": None, "operator": None})
	assert params == {
		"assetId": 7,
		"kind": "acknowledge",
		"message": "",
		"operator": DEFAULT_OPERATOR,
	}


@pytest.mark.parametrize(
	("payload", "reason"),
	[
		(None, "No event"),
		({"assetId": None, "kind": "note", "message": "x"}, "Select an asset"),
		({"assetId": "pump", "kind": "note", "message": "x"}, "Select an asset"),
		({"assetId": 1, "kind": "delete"}, "Unknown event kind"),
		({"assetId": 1, "kind": "note", "message": "   "}, "Write a note"),
		({"assetId": 1, "kind": "note", "message": "x" * 501}, "under 500"),
	],
)
def test_validate_rejects(payload: dict | None, reason: str) -> None:
	with pytest.raises(EventError, match=reason):
		validate(payload)


def test_handle_records_and_answers() -> None:
	with (
		patch("project.events.code.namedQuery") as namedQuery,
		patch("project.events.code.toRows", return_value=[{"id": 42, "time": 1234}]),
	):
		result = handle({"assetId": 2, "kind": "acknowledge", "operator": "bob"})
	assert result == {
		"ok": True,
		"id": 42,
		"time": 1234,
		"kind": "acknowledge",
		"text": "Acknowledgement recorded",
	}
	namedQuery.assert_called_once_with(
		"events/insert",
		{"assetId": 2, "kind": "acknowledge", "message": "", "operator": "bob"},
	)


def test_handle_answers_why_it_refused() -> None:
	with patch("project.events.code.namedQuery") as namedQuery:
		result = handle({"assetId": 2, "kind": "note", "message": ""})
	assert result == {"ok": False, "text": "Write a note first"}
	namedQuery.assert_not_called()


def test_handle_answers_when_the_insert_returns_nothing() -> None:
	with (
		patch("project.events.code.namedQuery"),
		patch("project.events.code.toRows", return_value=[]),
	):
		assert handle({"assetId": 2, "kind": "acknowledge"})["ok"] is False


def test_handle_logs_database_failures() -> None:
	with (
		patch("project.events.code.namedQuery", side_effect=RuntimeError("connection refused")),
		patch("project.events.code.LOGGER") as logger,
	):
		result = handle({"assetId": 2, "kind": "acknowledge"})
	assert result["ok"] is False
	assert "gateway log" in result["text"]
	assert "connection refused" in logger.error.call_args.args[0]


def test_send_asks_the_gateway_handler(system_util: MagicMock) -> None:
	system_util.sendRequest.return_value = {"ok": True, "text": "Note recorded"}
	with patch("project.events.code.sendRequest", system_util.sendRequest):
		assert send(3, "note", "hello", "ann") == {"ok": True, "text": "Note recorded"}
	system_util.sendRequest.assert_called_once_with(
		"project",
		"recordEvent",
		{"assetId": 3, "kind": "note", "message": "hello", "operator": "ann"},
		timeoutSec=10,
	)


def test_send_answers_when_the_gateway_does_not() -> None:
	with patch("project.events.code.sendRequest", side_effect=RuntimeError("timeout")):
		assert send(3, "acknowledge")["ok"] is False
	with patch("project.events.code.sendRequest", return_value=None):
		assert send(3, "acknowledge") == {"ok": False, "text": "No answer"}


EVENTS = [
	{
		"id": 2,
		"time": 900,
		"asset": "Blower 2",
		"area": "South",
		"kind": "note",
		"message": "Bearings on order",
		"operator": "engineer",
	},
	{
		"id": 1,
		"time": 100,
		"asset": "Blower 2",
		"area": "South",
		"kind": "status",
		"message": "Out of service",
		"operator": "system",
	},
]


def test_table_rows_label_the_kind() -> None:
	rows = tableRows(EVENTS)
	assert rows[0]["kind"] == "Note"
	assert rows[1]["kind"] == "Status"
	assert rows[0]["message"] == "Bearings on order"


def test_counts() -> None:
	assert counts(EVENTS, 86400 * 1000 + 500) == {
		"total": 2,
		"acknowledge": 0,
		"note": 1,
		"status": 1,
		"day": 1,
	}


def test_get_events_and_table() -> None:
	with (
		patch("project.events.code.namedQuery") as namedQuery,
		patch("project.events.code.toRows", return_value=EVENTS),
		patch("project.events.code.time.time", return_value=1.0),
	):
		assert getEvents(3, 5) == EVENTS
		table = getTable()
	assert namedQuery.call_args_list[0].args == ("events/list", {"assetId": 3, "limit": 5})
	assert namedQuery.call_args_list[1].args == ("events/list", {"assetId": 0, "limit": 200})
	assert table["counts"]["total"] == 2
	assert len(table["rows"]) == 2
