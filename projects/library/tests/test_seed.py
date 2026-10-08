"""Tests for library.seed and the repository's seed spec."""

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from library.seed.code import SECTIONS, MissingVariable, apply, applyFile, loadSpec, resolve

SPEC = Path(__file__).resolve().parents[3] / "gateway" / "seed" / "seed.json"


class FakeGateway:
	"""Records what library.seed creates; existing names per section."""

	def __init__(self, existing: dict[str, list[str]] | None = None, fail: str = "") -> None:
		self.names = existing or {}
		self.fail = fail
		self.created: list[tuple[str, str, dict[str, Any]]] = []

	def existing(self, section: str) -> list[str]:
		return self.names.get(section, [])

	def create(self, section: str, name: str, item: dict[str, Any]) -> bool | None:
		if f"{section}/{name}" == self.fail:
			raise RuntimeError("no such driver")
		if section == "gateway" and item == self.names.get("gateway-current"):
			return False
		self.created.append((section, name, item))
		return None


def env(**values: str):
	return values.get


def test_resolve_replaces_placeholders_recursively() -> None:
	item = {"url": "jdbc:${HOST}/db", "list": ["${PORT:-5432}"], "n": 1, "plain": "x"}
	assert resolve(item, env(HOST="db")) == {
		"url": "jdbc:db/db",
		"list": ["5432"],
		"n": 1,
		"plain": "x",
	}


def test_resolve_prefers_the_environment_over_the_default() -> None:
	assert resolve("${PORT:-5432}", env(PORT="6543")) == "6543"


def test_resolve_raises_for_a_missing_variable() -> None:
	with pytest.raises(MissingVariable, match="SECRET"):
		resolve({"a": ["${SECRET}"]}, env())


def test_apply_creates_only_missing_items_in_section_order() -> None:
	spec = {
		"alarmJournals": {"demo": {"type": "DATASOURCE"}},
		"databases": {"demo": {"url": "${URL}"}, "old": {"url": "x"}},
	}
	gateway = FakeGateway({"databases": ["old"]})
	log = MagicMock()
	result = apply(spec, gateway, log, env(URL="jdbc:postgresql://db/demo"))
	assert [(s, n) for s, n, _ in gateway.created] == [
		("databases", "demo"),
		("alarmJournals", "demo"),
	]
	assert gateway.created[0][2] == {"url": "jdbc:postgresql://db/demo"}
	assert result["created"] == ["databases/demo", "alarmJournals/demo"]
	assert "databases/demo" in log.info.call_args.args[0]


def test_apply_skips_items_missing_a_variable() -> None:
	log = MagicMock()
	result = apply(
		{"databases": {"demo": {"password": "${DB_PASSWORD}"}}}, FakeGateway(), log, env()
	)
	assert result["skipped"] == ["databases/demo"]
	assert "DB_PASSWORD" in log.warn.call_args.args[0]


def test_apply_records_failures_and_carries_on() -> None:
	spec = {"databases": {"a": {}, "b": {}}}
	gateway = FakeGateway(fail="databases/a")
	result = apply(spec, gateway, MagicMock(), env())
	assert result["failed"] == ["databases/a"]
	assert result["created"] == ["databases/b"]


def test_gateway_settings_are_applied_every_time() -> None:
	gateway = FakeGateway()
	apply({"gateway": {"auditProfile": "logins"}}, gateway, MagicMock(), env())
	assert gateway.created == [("gateway", "settings", {"auditProfile": "logins"})]


def test_nothing_logged_at_info_when_nothing_changes() -> None:
	log = MagicMock()
	apply({"databases": {"demo": {}}}, FakeGateway({"databases": ["demo"]}), log, env())
	log.info.assert_not_called()


def test_load_spec_rejects_unknown_sections(tmp_path: Path) -> None:
	spec = tmp_path / "seed.json"
	spec.write_text(json.dumps({"$comment": "ok", "databsaes": {}}))
	with pytest.raises(ValueError, match="databsaes"):
		loadSpec(str(spec))


def test_load_spec_of_a_missing_file_is_empty(tmp_path: Path) -> None:
	assert loadSpec(str(tmp_path / "none.json")) == {}


def test_apply_file_does_nothing_on_8_3() -> None:
	util: MagicMock = sys.modules["system.util"]  # type: ignore[assignment]
	util.getVersion.return_value.getMajor.return_value = 8
	util.getVersion.return_value.getMinor.return_value = 3
	assert applyFile(str(SPEC)) is None


def test_apply_file_uses_the_8_1_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
	util: MagicMock = sys.modules["system.util"]  # type: ignore[assignment]
	util.getVersion.return_value.getMajor.return_value = 8
	util.getVersion.return_value.getMinor.return_value = 1
	fake = FakeGateway()
	adapter = MagicMock(Gateway81=lambda: fake)
	monkeypatch.setitem(sys.modules, "library.gateway81", adapter)
	monkeypatch.setenv("GATEWAY_DB_DEMO_URL", "jdbc:postgresql://database:5432/demo")
	monkeypatch.setenv("GATEWAY_DB_DEMO_USER", "demo")
	monkeypatch.setenv("GATEWAY_DB_DEMO_PASSWORD", "secret")
	monkeypatch.setenv("DEMO_USERS_PASSWORD", "secret")
	result = applyFile(str(SPEC))
	assert result is not None
	assert result["skipped"] == [], "every placeholder in the repository spec has a variable here"
	assert [s for s, _, _ in fake.created] == [
		s for s in SECTIONS if s in json.loads(SPEC.read_text())
	]


def test_repository_spec_items_reference_items_it_defines() -> None:
	spec = loadSpec(str(SPEC))
	databases = set(spec["databases"])
	for section in ("alarmJournals", "auditProfiles"):
		for name, item in spec[section].items():
			assert item["settings"]["Datasource"] in databases, f"{section}/{name}"
	for name, item in spec["identityProviders"].items():
		assert item["userSource"] in spec["userSources"], name
	for item in spec["alarmNotificationProfiles"].values():
		assert item["settings"]["EmailProfile"] in spec["emailProfiles"]
	assert spec["gateway"]["auditProfile"] in spec["auditProfiles"]
	for source in spec["userSources"].values():
		for user in source["users"]:
			assert set(user["roles"]) <= set(source["roles"]), user["name"]


def test_unchanged_gateway_settings_are_not_reported() -> None:
	log = MagicMock()
	gateway = FakeGateway({"gateway-current": {"auditProfile": "logins"}})  # type: ignore[dict-item]
	result = apply({"gateway": {"auditProfile": "logins"}}, gateway, log, env())
	assert result["created"] == []
	log.info.assert_not_called()
