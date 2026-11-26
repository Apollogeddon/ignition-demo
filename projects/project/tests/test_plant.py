"""Tests for project.plant, the Plant page's schematic and equipment popup."""

from unittest.mock import patch

from project.plant.code import (
	AIR,
	AMBER,
	DOSE,
	IDLE,
	SLOTS,
	TRACK,
	WATER,
	emptySlot,
	equipment,
	gauge,
	getEquipment,
	getPlant,
	lastEvent,
	openEquipment,
	plant,
	share,
	stage,
	symbolState,
	trend,
)

NOW = 1_000_000_000


def row(id_, name, kind, value, **fields):
	"""Return an assets/status row: online, North, rated 60 L/s, unless fields say otherwise."""
	base = {"area": "North", "online": True, "unit": "L/s", "capacity": 60.0}
	return {"id": id_, "name": name, "kind": kind, "value": value, **base, **fields}


ROWS = [
	row(8, "Intake well level", "level", 58.3, unit="%", capacity=100.0),
	row(1, "Intake pump 1", "pump", 49.4),
	row(2, "Intake pump 2", "pump", 45.2),
	row(7, "Intake pump 3", "pump", 0.0, online=False),
	row(3, "Blower 1", "blower", 1624.0, unit="m3/h", capacity=2000.0, area="South"),
	row(9, "Blower 2", "blower", 0.0, online=False, unit="m3/h", capacity=2000.0, area="South"),
	row(5, "Mixer", "mixer", 60.8, unit="rpm", capacity=80.0, area="South"),
	row(4, "Dosing pump", "pump", 2.1, capacity=3.0, area="South"),
	row(6, "Reservoir level", "level", 71.2, unit="%", capacity=100.0, area="East"),
	row(10, "Transfer pump 1", "pump", 34.9, capacity=45.0, area="East"),
	row(11, "Transfer pump 2", "pump", 0.0, capacity=45.0, area="East"),
	row(12, "Spare", "pump", 10.0, area=None),
]


def test_symbol_state() -> None:
	assert symbolState(row(1, "P", "pump", 4.0)) == "running"
	assert symbolState(row(1, "P", "pump", 0.0)) == "stopped"
	assert symbolState(row(1, "P", "pump", None)) == "stopped"
	assert symbolState(row(1, "P", "blower", 9.0, online=False)) == "faulted"
	assert symbolState(row(1, "L", "level", 50.0, online=False)) == "default"


def test_share_clamps_and_handles_missing_values() -> None:
	assert share(30.0, 60.0) == 0.5
	assert share(90.0, 60.0) == 1.0
	assert share(-1.0, 60.0) == 0.0
	assert share(None, 60.0) == 0.0
	assert share(10.0, 0) == 0.0


def test_stage_counts_running_and_sums_their_flow() -> None:
	slots = [
		{"running": True, "value": 40.0, "unit": "L/s"},
		{"running": False, "value": 5.0, "unit": "L/s"},
	]
	assert stage(slots) == {
		"flow": 40.0,
		"reading": "40.0 L/s",
		"running": 1,
		"count": 2,
		"caption": "1 of 2 running",
	}
	assert stage([])["caption"] == "0 of 0 running"


def test_plant_fills_every_slot() -> None:
	result = plant(ROWS)
	slots = result["slots"]
	assert set(slots) == {key for key, _ in SLOTS.values()}
	assert slots["intake1"]["state"] == "running"
	assert slots["intake1"]["reading"] == "49.4 L/s"
	assert slots["intake3"]["state"] == "faulted"
	assert slots["intake3"]["status"] == "Fault"
	assert slots["transfer2"]["status"] == "Stopped"
	assert slots["well"]["state"] == "default"
	assert slots["well"]["status"] == "Online"
	assert slots["reservoir"]["value"] == 71.2


def test_plant_stages_and_pipes() -> None:
	result = plant(ROWS)
	kpis = result["kpis"]
	assert kpis["intake"]["caption"] == "2 of 3 running"
	assert kpis["intake"]["reading"] == "94.6 L/s"
	assert kpis["air"]["reading"] == "1,624 m3/h"
	assert kpis["transfer"]["caption"] == "1 of 2 running"
	assert kpis["reservoir"] == "71.2 %"
	assert kpis["reservoirCaption"] == "Well 58.3 %"
	assert result["valve"] == "open"
	assert result["pipes"] == {"intake": WATER, "air": AIR, "dosing": DOSE, "transfer": WATER}


def test_plant_with_everything_stopped() -> None:
	stopped = [dict(r, value=0.0) for r in ROWS]
	result = plant(stopped)
	assert result["valve"] == "closed"
	assert set(result["pipes"].values()) == {IDLE}


def test_plant_without_rows_draws_empty_slots() -> None:
	result = plant([])
	assert result["slots"]["mixer"] == emptySlot("Mixer")
	assert result["slots"]["mixer"]["id"] is None
	assert result["kpis"]["intake"]["caption"] == "0 of 0 running"


def test_get_plant_queries_the_status() -> None:
	with patch("project.plant.code.getStatus", return_value=ROWS) as getStatus:
		assert getPlant()["slots"]["intake2"]["id"] == 2
	getStatus.assert_called_once_with()


def test_gauge_bands() -> None:
	pump = gauge(30.0, 60.0, "pump")
	assert pump["max"] == 60.0
	assert [(band["start"], band["end"], band["color"]) for band in pump["ranges"]] == [
		(-0.6, 60.0, AMBER),
		(-0.6, 51.0, TRACK),
	]
	level = gauge(None, 100.0, "level")
	assert level["value"] == 0.0
	assert [(band["start"], band["end"], band["color"]) for band in level["ranges"]] == [
		(-1.0, 100.0, AMBER),
		(-1.0, 85.0, TRACK),
		(-1.0, 15.0, AMBER),
	]


def test_trend_keeps_the_day_up_to_the_newest_reading() -> None:
	# 15-minute readings over two days, then live 5-minute ones
	quarter, five = 15 * 60 * 1000, 5 * 60 * 1000
	seeded = [{"time": i * quarter, "value": float(i)} for i in range(192)]
	end = seeded[-1]["time"]
	live = [{"time": end + (i + 1) * five, "value": 500.0} for i in range(12)]
	result = trend(seeded + live, "L/s")
	newest = live[-1]["time"]
	kept = [r for r in seeded + live if r["time"] > newest - 24 * 3600 * 1000]
	assert result["points"] == [r["value"] for r in kept]
	assert result["points"][-1] == 500.0
	assert result["low"] == "100 L/s"
	assert result["high"] == "500 L/s"
	assert result["mean"] == "186 L/s"
	assert trend([], "L/s")["low"] == "—"


def test_last_event() -> None:
	event = {"kind": "acknowledge", "time": NOW - 7_500_000, "operator": "operator"}
	assert lastEvent([event], NOW) == "Acknowledged 2h 05m ago by operator"
	assert lastEvent([dict(event, operator="")], NOW) == "Acknowledged 2h 05m ago"
	assert lastEvent([], NOW) == "No events recorded"


def test_equipment_shapes_one_asset() -> None:
	readings = [{"time": 1, "value": 40.0}, {"time": 2, "value": 50.0}]
	events = [{"kind": "note", "time": NOW - 60_000, "operator": "engineer"}]
	result = equipment(1, ROWS, readings, events, NOW)
	assert result["found"]
	assert result["name"] == "Intake pump 1"
	assert result["subtitle"] == "North area, Pump"
	assert result["status"] == "Running"
	assert result["pill"] == "Pill/Base Pill/Ok"
	assert result["rated"] == "Rated 60.0 L/s"
	assert result["load"] == "82% of rated"
	assert result["gauge"]["value"] == 49.4
	assert result["trend"]["points"] == [40.0, 50.0]
	assert result["lastEvent"] == "Note 1m 00s ago by engineer"


def test_equipment_faulted_and_missing() -> None:
	faulted = equipment(7, ROWS, [], [], NOW)
	assert faulted["pill"] == "Pill/Base Pill/Bad"
	assert faulted["status"] == "Fault"
	assert faulted["trend"]["points"] == []
	assert equipment(99, ROWS, [], [], NOW)["found"] is False
	unassigned = equipment(12, ROWS, [], [], NOW)
	assert unassigned["subtitle"] == "Unassigned area, Pump"


def test_get_equipment_runs_the_queries() -> None:
	with (
		patch("project.plant.code.namedQuery") as namedQuery,
		patch("project.plant.code.toRows", side_effect=[[{"time": 1, "value": 3.0}], []]),
		patch("project.plant.code.getStatus", return_value=ROWS),
	):
		result = getEquipment("2")
	assert result["name"] == "Intake pump 2"
	assert result["trend"]["points"] == [3.0]
	namedQuery.assert_any_call("readings/asset", {"assetId": 2})
	namedQuery.assert_any_call("events/list", {"assetId": 2, "limit": 1})


def test_get_equipment_without_an_id() -> None:
	with patch("project.plant.code.namedQuery") as namedQuery:
		assert getEquipment(None)["found"] is False
	namedQuery.assert_not_called()


def test_open_equipment_opens_the_popup(system) -> None:
	openEquipment(4, "Dosing pump", "[default]Assets/South/Dosing pump")
	openPopup = system["system.perspective"].openPopup
	openPopup.assert_called_once()
	args, kwargs = openPopup.call_args
	assert args == ("equipment", "Popup/Equipment")
	assert kwargs["params"] == {"assetId": 4, "tagPath": "[default]Assets/South/Dosing pump"}
	assert kwargs["title"] == "Dosing pump"
	assert kwargs["modal"]


def test_open_equipment_without_an_asset(system) -> None:
	openEquipment(None, "Mixer")
	system["system.perspective"].openPopup.assert_not_called()
