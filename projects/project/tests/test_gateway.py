"""Tests for project.gateway, the gateway event entry points."""

from unittest.mock import MagicMock, call, patch

from project.gateway.code import onStartup, onUpdate


def test_startup_imports_udts_before_syncing_instances() -> None:
	order = MagicMock()
	with (
		patch("project.gateway.code.ensureDatasource", order.ensureDatasource),
		patch("project.gateway.code.importAll", order.importAll),
		patch("project.gateway.code.syncInstances", order.syncInstances),
	):
		onStartup()
	assert order.mock_calls == [
		call.ensureDatasource("demo"),
		call.importAll("library"),
		call.syncInstances(),
	]


def test_startup_survives_a_missing_database() -> None:
	with (
		patch("project.gateway.code.ensureDatasource"),
		patch("project.gateway.code.importAll"),
		patch(
			"project.gateway.code.syncInstances", side_effect=RuntimeError("no connection 'demo'")
		),
		patch("project.gateway.code.LOGGER") as logger,
	):
		onStartup()
	assert "no connection" in logger.warn.call_args.args[0]


def test_update_exports_udts_and_survives_failures() -> None:
	with (
		patch("project.gateway.code.exportAll", side_effect=RuntimeError("read-only")) as exportAll,
		patch("project.gateway.code.LOGGER") as logger,
	):
		onUpdate("designer", {})
	exportAll.assert_called_once_with("library")
	assert "read-only" in logger.warn.call_args.args[0]


def test_startup_continues_when_the_connection_cannot_be_created() -> None:
	with (
		patch("project.gateway.code.ensureDatasource", side_effect=RuntimeError("bad driver")),
		patch("project.gateway.code.importAll") as importAll,
		patch("project.gateway.code.syncInstances"),
		patch("project.gateway.code.LOGGER") as logger,
	):
		onStartup()
	assert "bad driver" in logger.error.call_args.args[0]
	importAll.assert_called_once_with("library")
