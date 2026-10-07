"""Tests for library.log."""

from unittest.mock import MagicMock

from library.log.code import get


def test_loggers_are_prefixed(system_util: MagicMock) -> None:
	get("assets")
	system_util.getLogger.assert_called_once_with("demo.assets")
