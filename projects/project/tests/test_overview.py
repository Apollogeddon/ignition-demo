"""Tests for project.overview, the Overview page's data."""

from unittest.mock import MagicMock, patch

from project.overview.code import (
	OTHER_COLOR,
	ago,
	areaAssets,
	areaColor,
	areas,
	flowSeries,
	gatewayRelease,
	getFlowSeries,
	getOverview,
	kpis,
	overview,
	pie,
	release,
)

NOW = 1_000_000_000

ROWS = [
	{
		"id": 1,
		"name": "Intake pump 1",
		"area": "North",
		"area_description": "Intake and pumping",
		"kind": "pump",
		"online": True,
		"unit": "L/s",
		"value": 40.25,
		"event_ms": None,
	},
	{
		"id": 7,
		"name": "Intake pump 3",
		"area": "North",
		"area_description": "Intake and pumping",
		"kind": "pump",
		"online": False,
		"unit": "L/s",
		"value": 0.0,
		"event_ms": NOW - 7_500_000,
	},
	{
		"id": 6,
		"name": "Reservoir level",
		"area": "East",
		"area_description": "Storage",
		"kind": "level",
		"online": True,
		"unit": "%",
		"value": 64.0,
		"event_ms": NOW - 3_600_000,
	},
	{
		"id": 10,
		"name": "Transfer pump 1",
		"area": "East",
		"area_description": "Storage",
		"kind": "pump",
		"online": True,
		"unit": "L/s",
		"value": None,
		"event_ms": None,
	},
	{
		"id": 12,
		"name": "Spare",
		"area": None,
		"area_description": None,
		"kind": "pump",
		"online": True,
		"unit": "L/s",
		"value": 2.0,
		"event_ms": None,
	},
]


def test_kpis() -> None:
	assert kpis(ROWS, NOW) == {
		"total": 5,
		"online": 4,
		"offline": 1,
		"availability": "80%",
		"flow": "42.2",
		"lastEvent": NOW - 3_600_000,
		"lastEventAgo": "1h 00m ago",
	}


def test_kpis_of_nothing() -> None:
	result = kpis([], NOW)
	assert result["total"] == 0
	assert result["availability"] == "—"
	assert result["lastEventAgo"] == "No events yet"


def test_ago() -> None:
	assert ago(NOW - 90_000, NOW) == "1m 30s ago"
	assert ago(None, NOW) == "—"


def test_areas_in_plant_order_with_counts_and_flow() -> None:
	cards = areas(ROWS)
	assert [c["area"] for c in cards] == ["North", "East", "Unassigned"]
	assert cards[0] == {
		"area": "North",
		"description": "Intake and pumping",
		"color": "#2563EB",
		"count": 2,
		"online": 1,
		"offline": 1,
		"flow": "40.2",
	}
	assert cards[1]["flow"] == "0.0"
	assert cards[2]["color"] == OTHER_COLOR


def test_area_color() -> None:
	assert areaColor("South") == "#0D9488"
	assert areaColor("West") == OTHER_COLOR


def test_pie_matches_the_cards() -> None:
	assert pie(areas(ROWS)) == {
		"data": [
			{"label": "North", "value": 2},
			{"label": "East", "value": 2},
			{"label": "Unassigned", "value": 1},
		],
		"colors": ["#2563EB", "#D97706", OTHER_COLOR],
	}


def test_overview_combines_the_parts() -> None:
	result = overview(ROWS, NOW)
	assert set(result) == {"kpis", "areas", "pie", "assets"}
	assert result["kpis"]["areas"] == 3
	assert [row["id"] for row in areaAssets(result["assets"], "East")] == [6, 10]


def test_get_overview_runs_one_query() -> None:
	with (
		patch("project.overview.code.getStatus", return_value=ROWS) as getStatus,
		patch("project.overview.code.time.time", return_value=NOW / 1000.0),
	):
		assert getOverview()["kpis"]["lastEventAgo"] == "1h 00m ago"
	getStatus.assert_called_once_with()


def test_flow_series_pivots_and_fills_missing_areas() -> None:
	rows = [
		{"time": 2, "area": "East", "flow": 5.0},
		{"time": 1, "area": "North", "flow": 10.0},
		{"time": 1, "area": "East", "flow": 4.0},
		{"time": 2, "area": "North", "flow": 11.0},
		{"time": 3, "area": "North", "flow": 12.0},
	]
	assert flowSeries(rows) == [
		{"time": 1, "North": 10.0, "East": 4.0},
		{"time": 2, "North": 11.0, "East": 5.0},
		{"time": 3, "North": 12.0, "East": 0.0},
	]


def test_get_flow_series_runs_the_named_query() -> None:
	with (
		patch("project.overview.code.namedQuery") as namedQuery,
		patch("project.overview.code.toRows", return_value=[]),
	):
		assert getFlowSeries() == []
	namedQuery.assert_called_once_with("readings/flowByArea")


def test_release(system_util: MagicMock) -> None:
	version = MagicMock()
	version.getMajor.return_value = 8
	version.getMinor.return_value = 1
	version.getRevision.return_value = 55
	assert release(version) == "Ignition 8.1.55"
	system_util.getVersion.return_value = version
	assert gatewayRelease() == "Ignition 8.1.55"
