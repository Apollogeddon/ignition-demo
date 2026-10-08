"""Tests for project.gateway, the gateway event entry points."""

from unittest.mock import MagicMock, call, patch

from project.gateway.code import onStartup, onUpdate, syncWhenReady


def test_startup_seeds_imports_udts_then_syncs_in_the_background() -> None:
	order = MagicMock()
	with (
		patch("project.gateway.code.applyFile", order.applyFile),
		patch("project.gateway.code.importAll", order.importAll),
		patch("project.gateway.code.invokeAsynchronous", order.invokeAsynchronous),
	):
		onStartup()
	assert order.mock_calls == [
		call.applyFile(),
		call.importAll("library"),
		call.invokeAsynchronous(syncWhenReady),
	]


def test_startup_continues_when_the_seed_fails() -> None:
	with (
		patch("project.gateway.code.applyFile", side_effect=RuntimeError("bad driver")),
		patch("project.gateway.code.importAll") as importAll,
		patch("project.gateway.code.invokeAsynchronous"),
		patch("project.gateway.code.LOGGER") as logger,
	):
		onStartup()
	assert "bad driver" in logger.error.call_args.args[0]
	importAll.assert_called_once_with("library")


def test_sync_retries_until_the_database_is_up() -> None:
	with (
		patch(
			"project.gateway.code.syncInstances",
			side_effect=[RuntimeError("FAULTED"), RuntimeError("FAULTED"), 6],
		) as sync,
		patch("project.gateway.code.time.sleep") as sleep,
	):
		assert syncWhenReady(attempts=5, delay=2) is True
	assert sync.call_count == 3
	assert sleep.call_args_list == [call(2), call(2)]


def test_sync_gives_up_with_a_warning() -> None:
	with (
		patch(
			"project.gateway.code.syncInstances", side_effect=RuntimeError("no connection 'demo'")
		),
		patch("project.gateway.code.time.sleep"),
		patch("project.gateway.code.LOGGER") as logger,
	):
		assert syncWhenReady(attempts=3, delay=0) is False
	assert "no connection" in logger.warn.call_args.args[0]


def test_update_exports_udts_and_survives_failures() -> None:
	with (
		patch("project.gateway.code.exportAll", side_effect=RuntimeError("read-only")) as exportAll,
		patch("project.gateway.code.LOGGER") as logger,
	):
		onUpdate("designer", {})
	exportAll.assert_called_once_with("library")
	assert "read-only" in logger.warn.call_args.args[0]
