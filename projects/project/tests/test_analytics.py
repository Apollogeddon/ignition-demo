"""Tests for project.analytics, the Analytics page's data."""

from unittest.mock import patch

from project.analytics.code import (
	HEAT,
	HEAT_EMPTY,
	analytics,
	chart,
	gauges,
	getAnalytics,
	heatColor,
	heatmap,
	hourly,
	output,
	utilisation,
)
from project.overview.code import AREA_COLORS

HOUR = 3_600_000


def hourRow(time, hour, area, kind, total, **fields):
	"""Return a readings/hourly row: Monday's, its mean the total, unless fields say otherwise."""
	row = {"time": time, "hour": hour, "area": area, "kind": kind, "total": total}
	return {**row, "day": "Mon 23 Nov", "mean": total, **fields}


HOURLY = [
	hourRow(0, 22, "North", "pump", 100.0, mean=50.0),
	hourRow(0, 22, "East", "pump", 50.0, mean=25.0),
	hourRow(0, 22, "East", "level", 70.0),
	hourRow(0, 22, "South", "mixer", 60.0),
	hourRow(HOUR, 23, "East", "level", 72.0),
	hourRow(HOUR, 23, "North", "pump", 120.0),
	hourRow(2 * HOUR, 0, "North", "pump", 80.0, day="Tue 24 Nov"),
	hourRow(2 * HOUR, 0, "East", "pump", 60.0, day="Tue 24 Nov"),
]


def status(id_, area, kind, value, capacity, **fields):
	"""Return an assets/status row, online unless fields say otherwise."""
	row = {"id": id_, "area": area, "kind": kind, "value": value, "capacity": capacity}
	return {**row, "online": True, **fields}


STATUS = [
	status(1, "North", "pump", 50.0, 60.0),
	status(2, "North", "pump", 40.0, 60.0),
	status(7, "North", "pump", 0.0, 60.0, online=False),
	status(8, "North", "level", 60.0, 100.0),
	status(3, "South", "blower", 1000.0, 2000.0),
	status(6, "East", "level", 70.0, 100.0),
	status(10, "East", "pump", 45.0, 45.0),
	status(12, None, "pump", 1.0, 0.0),
]


def test_hourly_pivots_the_measures() -> None:
	points = hourly(HOURLY)
	assert [point["time"] for point in points] == [0, HOUR, 2 * HOUR]
	first = points[0]
	assert first["label"] == "Mon 22:00"
	assert first["intake"] == 100.0
	assert first["delivered"] == 50.0
	assert first["volume"] == 180.0
	assert first["reservoir"] == 70.0
	assert points[1]["delivered"] is None
	assert points[1]["volume"] is None
	assert points[2]["label"] == "Tue 00:00"
	assert points[2]["reservoir"] is None


def test_chart_keeps_hours_with_a_series() -> None:
	points = [*hourly(HOURLY), {"label": "Tue 01:00", "volume": None, "reservoir": None}]
	assert chart(points) == [
		{"label": "Mon 22:00", "volume": 180.0, "reservoir": 70.0},
		{"label": "Mon 23:00", "volume": None, "reservoir": 72.0},
		{"label": "Tue 00:00", "volume": 216.0, "reservoir": None},
	]


def test_output_sums_the_last_day() -> None:
	points = [{"volume": 10.0}] * 30 + [{"volume": None}]
	assert output(points) == {"volume": 230, "hours": 23}
	assert output([]) == {"volume": 0, "hours": 0}


def test_heat_color_steps() -> None:
	assert heatColor(None, 0, 10) is None
	assert heatColor(0, 0, 10) == 0
	assert heatColor(10, 0, 10) == len(HEAT) - 1
	assert heatColor(5, 0, 10) == len(HEAT) // 2
	assert heatColor(-5, 0, 10) == 0
	assert heatColor(3, 3, 3) == len(HEAT) // 2


def test_heatmap_grid() -> None:
	grid = heatmap(hourly(HOURLY))
	assert [row["label"] for row in grid["rows"]] == ["Mon 23 Nov", "Tue 24 Nov"]
	monday = grid["rows"][0]["cells"]
	assert len(monday) == 24
	assert monday[0] == {
		"color": HEAT_EMPTY,
		"dark": False,
		"text": "",
		"tooltip": "Mon 23 Nov 00:00, no data",
	}
	assert monday[22]["text"] == "100"
	assert monday[22]["tooltip"] == "Mon 23 Nov 22:00, 100.0 L/s"
	assert monday[23]["color"] == HEAT[-1]
	assert monday[23]["dark"]
	assert grid["rows"][1]["cells"][0]["color"] == HEAT[0]
	assert grid["low"] == "80 L/s"
	assert grid["high"] == "120 L/s"
	assert [cell["text"] for cell in grid["hours"]][:4] == ["00", "", "", "03"]
	assert len(grid["scale"]) == len(HEAT)


def test_heatmap_without_points() -> None:
	grid = heatmap([])
	assert grid["rows"] == []
	assert grid["low"] == "—"


def test_gauges() -> None:
	result = gauges(STATUS)
	assert result["availability"] == {"value": 87.5, "caption": "7 of 8 assets online"}
	assert result["intake"] == {
		"value": 90.0,
		"max": 180.0,
		"caption": "90 of 180 L/s rated, 50%",
	}
	assert result["reservoir"]["value"] == 70.0


def test_gauges_without_rows() -> None:
	result = gauges([])
	assert result["availability"]["value"] == 0.0
	assert result["intake"]["max"] == 100.0
	assert result["intake"]["caption"].endswith("—")
	assert result["reservoir"]["value"] == 0.0


def test_utilisation_per_area_in_order() -> None:
	areas = utilisation(STATUS)
	assert [area["area"] for area in areas] == ["North", "South", "East", "Unassigned"]
	north = areas[0]
	# (50/60 + 40/60 + offline 0 + 60/100) / 4
	assert north["value"] == 52.5
	assert north["text"] == "52%"
	assert north["caption"] == "3 of 4 online"
	assert north["color"] == AREA_COLORS["North"]
	assert areas[2]["value"] == 85.0
	assert areas[3]["value"] == 0.0


def test_analytics_combines_everything() -> None:
	result = analytics(STATUS, HOURLY)
	assert set(result) == {"gauges", "output", "chart", "heatmap", "areas"}
	assert result["output"]["volume"] == 396


def test_get_analytics_runs_the_queries() -> None:
	with (
		patch("project.analytics.code.namedQuery") as namedQuery,
		patch("project.analytics.code.toRows", return_value=HOURLY),
		patch("project.analytics.code.getStatus", return_value=STATUS),
	):
		result = getAnalytics()
	namedQuery.assert_called_once_with("readings/hourly")
	assert len(result["chart"]) == 3
