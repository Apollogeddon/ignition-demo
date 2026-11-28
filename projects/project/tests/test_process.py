"""Tests for project.process, the plant model that drives the assets' tags."""

import random
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from project.process import code
from project.process.code import (
	MESSAGES,
	RESET_SECONDS,
	TICK_SECONDS,
	basePath,
	demand,
	dueToLog,
	initial,
	members,
	motor,
	readValues,
	recordChanges,
	step,
	tick,
	valveOpening,
	writeValues,
)

ASSETS = [
	{"id": 1, "name": "Intake pump 1", "area": "North", "kind": "pump", "capacity": 60.0},
	{"id": 2, "name": "Intake pump 2", "area": "North", "kind": "pump", "capacity": 60.0},
	{"id": 8, "name": "Intake well level", "area": "North", "kind": "level", "capacity": 100.0},
	{"id": 3, "name": "Blower 1", "area": "South", "kind": "blower", "capacity": 2000.0},
	{"id": 4, "name": "Dosing pump", "area": "South", "kind": "pump", "capacity": 3.0},
	{"id": 5, "name": "Mixer", "area": "South", "kind": "mixer", "capacity": 80.0},
	{"id": 6, "name": "Reservoir level", "area": "East", "kind": "level", "capacity": 100.0},
	{"id": 10, "name": "Transfer pump 1", "area": "East", "kind": "pump", "capacity": 45.0},
]
MOTORS = [a["name"] for a in ASSETS if a["kind"] != "level"]
NOON = 12 * 3600.0


class Steady:
	"""A generator with no noise and no faults."""

	def random(self) -> float:
		return 1.0

	def gauss(self, _mu: float, _sigma: float) -> float:
		return 0.0


def running(well: float = 50.0, reservoir: float = 70.0) -> dict[str, dict[str, Any]]:
	values: dict[str, dict[str, Any]] = {
		name: {"value": 0.0, "running": True, "fault": False, "cmdRun": True} for name in MOTORS
	}
	values["Intake well level"] = {"value": well}
	values["Reservoir level"] = {"value": reservoir}
	return values


def test_running_pumps_move_water_and_levels_follow() -> None:
	out, tripped, changes = step(ASSETS, running(), NOON, Steady(), {})
	intake = out["Intake pump 1"]["value"]
	# an intake pump draws BASE + HEAD x well of its rated flow
	assert intake == pytest.approx(60.0 * (0.45 + 0.0035 * 50))
	assert out["Transfer pump 1"]["value"] == pytest.approx(45.0 * demand(NOON))
	assert out["Blower 1"]["value"] == pytest.approx(2000.0 * 0.69)
	assert out["Blower 1"]["pressure"] == pytest.approx(48.0)
	assert out["Mixer"]["value"] == pytest.approx(55.0)
	# the valve is wide open at 70 %, so the dosing pump doses 2 % of both intakes
	assert out["Dosing pump"]["value"] == pytest.approx(0.02 * 2 * intake)
	assert out["Intake pump 1"]["speed"] == pytest.approx(100 * intake / 60.0)
	assert out["Intake pump 1"]["running"] is True
	assert tripped == {}
	assert changes == []
	# two intake pumps outdraw the river at 50 %, and outfill one transfer pump
	assert out["Intake well level"]["value"] != 50.0
	assert out["Reservoir level"]["value"] > 70.0


def test_a_stopped_pump_reads_zero_and_records_a_stop() -> None:
	values = running()
	values["Intake pump 2"]["cmdRun"] = False
	out, _, changes = step(ASSETS, values, NOON, Steady(), {})
	assert out["Intake pump 2"] == {"value": 0.0, "running": False, "fault": False, "speed": 0.0}
	assert changes == [("Intake pump 2", "stop")]


def test_the_outlet_valve_throttles_as_the_reservoir_fills() -> None:
	assert valveOpening(50.0) == 1.0
	assert valveOpening(87.5) == pytest.approx(0.5)
	assert valveOpening(99.0) == 0.0
	out, _, _ = step(ASSETS, running(reservoir=99.0), NOON, Steady(), {})
	# no treated water reaches the reservoir, so the transfer pump drains it
	assert out["Reservoir level"]["value"] < 99.0
	assert out["Dosing pump"]["value"] == 0.0


def test_tanks_stay_between_empty_and_full() -> None:
	values = running(well=0.0, reservoir=100.0)
	out, _, _ = step(ASSETS, values, NOON, Steady(), {})
	assert 0.0 <= out["Intake well level"]["value"] <= 100.0
	assert 0.0 <= out["Reservoir level"]["value"] <= 100.0


def test_demand_peaks_in_the_day_and_dips_at_night() -> None:
	night = demand(3 * 3600.0)
	assert night < demand(NOON)
	assert all(0.4 < demand(h * 3600.0) < 1.0 for h in range(24))


def test_a_running_motor_trips_and_records_only_the_trip() -> None:
	rng = MagicMock(spec=random.Random)
	rng.random.return_value = 0.0
	assert motor({"running": True, "cmdRun": True}, None, NOON, rng) == (False, True, NOON, "trip")


def test_a_trip_resets_after_its_time_and_restarts_quietly() -> None:
	rng = Steady()
	value = {"running": False, "fault": True, "cmdRun": True}
	assert motor(value, NOON, NOON + 60, rng) == (False, True, NOON, None)
	later = NOON + RESET_SECONDS
	assert motor(value, NOON, later, rng) == (True, False, None, "reset")


def test_a_fault_with_no_trip_time_counts_from_now() -> None:
	assert motor({"fault": True}, None, NOON, Steady()) == (False, True, NOON, None)


def test_an_operator_restart_clears_the_trip() -> None:
	# the popup's Start writes fault false: the motor runs and records a start
	run = motor({"running": False, "fault": False, "cmdRun": True}, None, NOON, Steady())
	assert run == (True, False, None, "start")


def test_step_carries_trip_times_and_transitions() -> None:
	values = running()
	values["Blower 1"].update(running=False, fault=True)
	out, tripped, changes = step(ASSETS, values, NOON, Steady(), {"Blower 1": NOON - 30})
	assert tripped == {"Blower 1": NOON - 30}
	assert out["Blower 1"]["value"] == 0.0
	assert out["Blower 1"]["fault"] is True
	assert changes == []


def test_initial_starts_from_the_database_without_recording_starts() -> None:
	assets = [
		dict(ASSETS[0], online=True),
		dict(ASSETS[1], online=False),
		dict(ASSETS[2], value=42.0),
	]
	fresh = {"Intake pump 1": {"cmdRun": True}, "Intake pump 2": {"cmdRun": True}}
	start = initial(assets, fresh)
	assert start["Intake pump 1"] == {"cmdRun": True, "running": True}
	assert start["Intake pump 2"] == {"cmdRun": True, "fault": True, "running": False}
	assert start["Intake well level"] == {"value": 42.0}
	_, _, changes = step(assets, start, NOON, Steady(), {})
	assert changes == []


def test_paths_and_members() -> None:
	assert basePath(ASSETS[0]) == "[default]Assets/North/Intake pump 1"
	assert [m for _, m in members(ASSETS[2])] == ["value"]
	assert ("pressure", "pressure") in members(ASSETS[3])
	assert ("cmdRun", "motor/cmdRun") in members(ASSETS[0])


def test_read_and_write_never_touch_the_operator_command(system: dict[str, MagicMock]) -> None:
	tag = system["system.tag"]
	assets = [ASSETS[0], ASSETS[2]]
	qv = MagicMock()
	qv.value = 1.5
	tag.readBlocking.return_value = [qv] * 6
	with (
		patch.object(code, "readBlocking", tag.readBlocking),
		patch.object(code, "writeBlocking", tag.writeBlocking),
	):
		values = readValues(assets)
		assert values["Intake pump 1"]["cmdRun"] == 1.5
		writeValues(assets, {"Intake pump 1": {"value": 2.0, "cmdRun": False, "running": True}})
	paths, written = tag.writeBlocking.call_args.args
	assert paths == [
		"[default]Assets/North/Intake pump 1/value",
		"[default]Assets/North/Intake pump 1/motor/running",
	]
	assert written == [2.0, True]


def test_readings_are_due_once_per_slot() -> None:
	due, slot = dueToLog(NOON, None)
	assert due
	assert dueToLog(NOON + 60, slot) == (False, slot)
	assert dueToLog(NOON + 300, slot)[0]


def test_changes_become_status_events() -> None:
	with patch.object(code, "namedQuery") as query:
		assert recordChanges(ASSETS, [("Blower 1", "trip")]) == 1
	query.assert_called_once_with(
		"events/insert",
		{"assetId": 3, "kind": "status", "message": MESSAGES["trip"], "operator": "Process"},
	)


def test_tick_steps_writes_records_and_logs() -> None:
	memory: dict[str, Any] = {"tripped": {}, "logSlot": None, "started": True}
	with (
		patch.object(code, "state", return_value=memory),
		patch.object(code, "loadAssets", return_value=ASSETS),
		patch.object(code, "readValues", return_value=running()),
		patch.object(code, "step", return_value=({}, {}, [("Mixer", "stop")])) as stepped,
		patch.object(code, "writeValues") as written,
		patch.object(code, "recordChanges", return_value=1),
		patch.object(code, "notifySessions") as notified,
		patch.object(code, "logReadings") as logged,
	):
		tick(NOON)
		tick(NOON + TICK_SECONDS)
	assert stepped.call_count == 2
	assert written.call_count == 2
	assert notified.call_count == 2
	# once per LOG_MINUTES slot
	assert logged.call_args_list == [call(ASSETS, {})]


def test_a_failed_tick_is_logged_not_raised() -> None:
	with (
		patch.object(code, "state", return_value={"tripped": {}, "logSlot": None}),
		patch.object(code, "loadAssets", side_effect=RuntimeError("database down")),
		patch.object(code, "LOGGER") as logger,
	):
		tick(NOON)
	assert "database down" in logger.warn.call_args.args[0]


def test_start_writes_the_command_and_resets_a_trip() -> None:
	good = MagicMock()
	good.isGood.return_value = True
	with patch.object(code, "writeBlocking", return_value=[good, good]) as write:
		assert code.command("[default]Assets/South/Mixer", run=True) == {
			"ok": True,
			"text": "Starting",
		}
	write.assert_called_once_with(
		["[default]Assets/South/Mixer/motor/cmdRun", "[default]Assets/South/Mixer/motor/fault"],
		[True, False],
	)


def test_stop_only_clears_the_command_and_reports_a_bad_write() -> None:
	bad = MagicMock()
	bad.isGood.return_value = False
	with patch.object(code, "writeBlocking", return_value=[bad]) as write:
		result = code.command("[default]Assets/South/Mixer", run=False)
	write.assert_called_once_with(["[default]Assets/South/Mixer/motor/cmdRun"], [False])
	assert result["ok"] is False


def test_a_fault_left_as_read_is_not_written_back() -> None:
	# an operator's Start may clear the trip between the read and the write
	out = {"Blower 1": {"value": 0.0, "fault": True}, "Mixer": {"value": 55.0, "fault": False}}
	read = {"Blower 1": {"fault": True}, "Mixer": {"fault": True}}
	kept = code.unchangedFaults(out, read)
	assert kept["Blower 1"] == {"value": 0.0}
	# a reset the model made is written
	assert kept["Mixer"] == {"value": 55.0, "fault": False}
	assert out["Blower 1"]["fault"] is True


def test_a_failed_log_is_retried_next_tick() -> None:
	memory: dict[str, Any] = {"tripped": {}, "logSlot": None, "started": True}
	with (
		patch.object(code, "state", return_value=memory),
		patch.object(code, "loadAssets", return_value=ASSETS),
		patch.object(code, "readValues", return_value=running()),
		patch.object(code, "step", return_value=({}, {}, [])),
		patch.object(code, "writeValues"),
		patch.object(code, "logReadings", side_effect=[RuntimeError("db"), None]) as logged,
		patch.object(code, "LOGGER"),
	):
		tick(NOON)
		assert memory["logSlot"] is None
		tick(NOON + TICK_SECONDS)
	assert logged.call_count == 2
	assert memory["logSlot"] is not None
