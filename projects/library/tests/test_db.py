"""Tests for library.db on both Ignition versions."""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest
from library.db import code


def test_uses_exec_query_on_8_3() -> None:
	db: MagicMock = sys.modules["system.db"]  # type: ignore[assignment]
	importlib.reload(code)
	assert code.namedQuery("assets/list") is db.execQuery.return_value
	db.execQuery.assert_called_once_with("assets/list", {})


def test_falls_back_to_run_named_query_on_8_1(monkeypatch: pytest.MonkeyPatch) -> None:
	db81 = types.ModuleType("system.db")
	db81.runNamedQuery = MagicMock(name="runNamedQuery")  # type: ignore[attr-defined]
	monkeypatch.setitem(sys.modules, "system.db", db81)
	importlib.reload(code)
	try:
		code.namedQuery("assets/list", {"area": "North"})
		db81.runNamedQuery.assert_called_once_with("assets/list", {"area": "North"})  # type: ignore[attr-defined]
	finally:
		monkeypatch.undo()
		importlib.reload(code)
