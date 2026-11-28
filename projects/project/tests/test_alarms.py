"""Tests for project.alarms, the alarm counts."""

from unittest.mock import MagicMock, patch

from project.alarms import code
from project.alarms.code import counts


def event(state: str, priority: str = "Medium") -> MagicMock:
	alarm = MagicMock()
	alarm.getState.return_value = state
	alarm.getPriority.return_value = priority
	return alarm


def test_counts_active_unacknowledged_and_high() -> None:
	events = [
		event("ActiveUnacked", "High"),
		event("ActiveAcked", "Medium"),
		event("ClearUnacked", "Critical"),
		event("ActiveUnacked", "Critical"),
	]
	assert counts(events) == {"active": 3, "unacked": 3, "high": 2}


def test_no_alarms() -> None:
	assert counts([]) == {"active": 0, "unacked": 0, "high": 0}


def test_a_failed_query_counts_nothing() -> None:
	with (
		patch.object(code, "queryStatus", side_effect=RuntimeError("no provider")),
		patch.object(code, "LOGGER") as logger,
	):
		assert code.getCounts() == {"active": 0, "unacked": 0, "high": 0}
	assert "no provider" in logger.warn.call_args.args[0]


def test_queries_the_asset_alarms() -> None:
	with patch.object(code, "queryStatus", return_value=[event("ActiveUnacked")]) as query:
		assert code.getCounts()["active"] == 1
	kwargs = query.call_args.kwargs
	assert kwargs["source"] == ["*Assets/*"]
	assert set(kwargs["state"]) == {"ActiveUnacked", "ActiveAcked", "ClearUnacked"}


def test_counts_by_enum_name_not_display_text() -> None:
	state = MagicMock()
	state.name.return_value = "ActiveUnacked"
	state.configure_mock(**{"__str__.return_value": "Active, Unacknowledged"})
	alarm = MagicMock()
	alarm.getState.return_value = state
	alarm.getPriority.return_value = "High"
	assert counts([alarm]) == {"active": 1, "unacked": 1, "high": 1}
