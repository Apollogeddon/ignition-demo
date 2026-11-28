"""Tests for library.db on both Ignition versions."""

import importlib
import sys
from unittest.mock import MagicMock

import pytest
from library.db import code


def test_uses_exec_query_on_8_3(system: dict[str, MagicMock]) -> None:
	db = system["system.db"]
	importlib.reload(code)
	assert code.namedQuery("assets/list") is db.execQuery.return_value
	db.execQuery.assert_called_once_with("assets/list", {})


def test_falls_back_to_run_named_query_on_8_1(monkeypatch: pytest.MonkeyPatch) -> None:
	# 8.1's system.db has runNamedQuery and no execQuery
	db81 = MagicMock(name="system.db", spec=["runNamedQuery"])
	monkeypatch.setitem(sys.modules, "system.db", db81)
	importlib.reload(code)
	try:
		code.namedQuery("assets/list", {"area": "North"})
		db81.runNamedQuery.assert_called_once_with("assets/list", {"area": "North"})
	finally:
		monkeypatch.undo()
		importlib.reload(code)


def test_runs_updates_with_exec_update_on_8_3(system: dict[str, MagicMock]) -> None:
	db = system["system.db"]
	importlib.reload(code)
	assert code.namedUpdate("readings/insert", {"value": 1.0}) is db.execUpdate.return_value
	db.execUpdate.assert_called_once_with("readings/insert", {"value": 1.0})


def test_runs_updates_with_run_named_query_on_8_1(monkeypatch: pytest.MonkeyPatch) -> None:
	db81 = MagicMock(name="system.db", spec=["runNamedQuery"])
	monkeypatch.setitem(sys.modules, "system.db", db81)
	importlib.reload(code)
	try:
		code.namedUpdate("readings/insert")
		db81.runNamedQuery.assert_called_once_with("readings/insert", {})
	finally:
		monkeypatch.undo()
		importlib.reload(code)
