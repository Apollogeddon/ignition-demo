"""Tests for library.config."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from library.config.code import configuredByApi, ensureDatasource

ENV = {
	"GATEWAY_DB_DEMO_URL": "jdbc:postgresql://database:5432/demo",
	"GATEWAY_DB_DEMO_USER": "demo",
	"GATEWAY_DB_DEMO_PASSWORD": "secret",
}


def module(name: str) -> MagicMock:
	return sys.modules[name]  # type: ignore[return-value]


def gateway(major: int, minor: int) -> None:
	module("system.util").getVersion.return_value.getMajor.return_value = major
	module("system.util").getVersion.return_value.getMinor.return_value = minor


@pytest.mark.parametrize(("major", "minor", "api"), [(8, 1, False), (8, 3, True), (9, 0, True)])
def test_configured_by_api_from_8_3(major: int, minor: int, api: bool) -> None:
	gateway(major, minor)
	assert configuredByApi() is api


def test_creates_a_missing_connection_on_8_1() -> None:
	gateway(8, 1)
	with patch("library.config.code.toRows", return_value=[{"Name": "other"}]):
		assert ensureDatasource("demo", ENV.get) is True
	module("system.db").addDatasource.assert_called_once_with(
		"PostgreSQL",
		"demo",
		"Created from the environment by the gateway startup event",
		"jdbc:postgresql://database:5432/demo",
		"demo",
		"secret",
	)


def test_driver_can_be_chosen() -> None:
	gateway(8, 1)
	env = dict(ENV, GATEWAY_DB_DEMO_DRIVER="MariaDB")
	with patch("library.config.code.toRows", return_value=[]):
		ensureDatasource("demo", env.get)
	assert module("system.db").addDatasource.call_args.args[0] == "MariaDB"


def test_existing_connection_is_left_alone() -> None:
	gateway(8, 1)
	with patch("library.config.code.toRows", return_value=[{"Name": "demo"}]):
		assert ensureDatasource("demo", ENV.get) is False
	module("system.db").addDatasource.assert_not_called()


def test_nothing_without_a_url() -> None:
	gateway(8, 1)
	assert ensureDatasource("demo", {}.get) is False
	module("system.db").addDatasource.assert_not_called()


def test_nothing_on_8_3() -> None:
	gateway(8, 3)
	assert ensureDatasource("demo", ENV.get) is False
	module("system.db").addDatasource.assert_not_called()
