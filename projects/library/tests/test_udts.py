"""Tests for library.udts, and checks on every project's UDT files."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from library.udts.code import definitions, exportAll, importAll, normalise

PROJECTS = Path(__file__).resolve().parents[2]
UDT_DIRS = sorted(p for p in PROJECTS.glob("*/src/udts") if (p / "index.json").is_file())


def module(name: str) -> MagicMock:
	return sys.modules[name]  # type: ignore[return-value]


def test_definitions_map_entries_to_files_and_folders() -> None:
	assert definitions("library", ["subTypes/motor", "pump"], "plant") == [
		(
			"subTypes/motor",
			"/usr/local/bin/ignition/assets/projects/library/udts/subTypes/motor.json",
			"[plant]_types_/subTypes",
		),
		(
			"pump",
			"/usr/local/bin/ignition/assets/projects/library/udts/pump.json",
			"[plant]_types_",
		),
	]


def test_definitions_reject_folder_only_entries() -> None:
	with pytest.raises(ValueError, match="invalid UDT index entry"):
		definitions("library", ["subTypes/"])


def test_normalise_sorts_keys_and_indents() -> None:
	assert normalise('{"b": 1, "a": {"d": 2, "c": 3}}') == (
		'{\n    "a": {\n        "c": 3,\n        "d": 2\n    },\n    "b": 1\n}\n'
	)


def test_import_all_follows_the_index_and_counts_failures() -> None:
	module("system.file").readFileAsString.return_value = '["subTypes/motor", "equipment/pump"]'
	tag = module("system.tag")
	tag.importTags.side_effect = [None, RuntimeError("bad definition")]
	assert importAll("library") == 1
	base = "/usr/local/bin/ignition/assets/projects/library/udts"
	assert tag.importTags.call_args_list == [
		call(base + "/subTypes/motor.json", "[default]_types_/subTypes", "o"),
		call(base + "/equipment/pump.json", "[default]_types_/equipment", "o"),
	]


def test_export_all_writes_normalised_files() -> None:
	file = module("system.file")
	file.readFileAsString.side_effect = ['["equipment/pump"]', '{"tags": [], "name": "pump"}']
	exportAll("library")
	path = "/usr/local/bin/ignition/assets/projects/library/udts/equipment/pump.json"
	module("system.tag").exportTags.assert_called_once_with(
		path, ["[default]_types_/equipment/pump"]
	)
	file.writeFile.assert_called_once_with(path, '{\n    "name": "pump",\n    "tags": []\n}\n')


def type_ids(tags: list[dict[str, object]]) -> set[str]:
	found: set[str] = set()
	for tag in tags:
		if tag.get("tagType") == "UdtInstance":
			found.add(str(tag["typeId"]))
		found |= type_ids(tag.get("tags", []))  # type: ignore[arg-type]
	return found


@pytest.mark.parametrize("udts", UDT_DIRS, ids=lambda p: p.parts[-3])
def test_index_lists_every_definition_in_dependency_order(udts: Path) -> None:
	index = json.loads((udts / "index.json").read_text("utf-8"))
	files = sorted(
		str(p.relative_to(udts).with_suffix("")).replace("\\", "/") for p in udts.rglob("*.json")
	)
	files.remove("index")
	assert sorted(index) == files, "udts/index.json must list every definition once"
	seen: set[str] = set()
	for entry in index:
		udt = json.loads((udts / (entry + ".json")).read_text("utf-8"))
		assert udt["name"] == entry.rpartition("/")[2], entry + ": name must match the file name"
		assert udt["tagType"] == "UdtType", entry
		missing = type_ids(udt["tags"]) - seen
		assert not missing, f"{entry} nests {sorted(missing)} before they are imported"
		seen.add(entry)


@pytest.mark.parametrize("udts", UDT_DIRS, ids=lambda p: p.parts[-3])
def test_definitions_are_normalised(udts: Path) -> None:
	for path in udts.rglob("*.json"):
		if path.name != "index.json":
			text = path.read_text("utf-8")
			assert text == normalise(text), f"{path} is not normalised"


def test_import_all_succeeds() -> None:
	module("system.file").readFileAsString.return_value = '["subTypes/motor"]'
	assert importAll("library") == 0
	module("system.tag").importTags.assert_called_once()


def test_normalise_drops_8_1_placeholders_and_sorts_members() -> None:
	exported_81 = {
		"name": "pump",
		"tagType": "UdtType",
		"tags": [
			{
				"name": "motor",
				"tagType": "UdtInstance",
				"typeId": "subTypes/motor",
				"tags": [
					{"name": "speed", "tagType": "AtomicTag"},
					{"name": "running", "tagType": "AtomicTag", "value": True},
				],
			},
			{"name": "flow", "tagType": "AtomicTag", "valueSource": "memory"},
		],
	}
	assert json.loads(normalise(json.dumps(exported_81))) == {
		"name": "pump",
		"tagType": "UdtType",
		"tags": [
			{"name": "flow", "tagType": "AtomicTag", "valueSource": "memory"},
			# the override on running is kept; the bare speed placeholder is not
			{
				"name": "motor",
				"tagType": "UdtInstance",
				"typeId": "subTypes/motor",
				"tags": [
					{"name": "running", "tagType": "AtomicTag", "value": True},
				],
			},
		],
	}


def test_normalise_keeps_bare_members_of_a_type() -> None:
	# outside an instance, a member with no other properties is a real definition
	udt = {
		"name": "t",
		"tagType": "UdtType",
		"tags": [{"name": "b", "tagType": "Folder"}, {"name": "a", "tagType": "AtomicTag"}],
	}
	assert [t["name"] for t in json.loads(normalise(json.dumps(udt)))["tags"]] == ["a", "b"]
