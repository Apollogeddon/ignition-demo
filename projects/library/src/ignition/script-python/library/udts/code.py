"""UDT definitions kept as files in each project's udts folder.

A project's definitions live in src/udts/<folder>/<name>.json and ship in the
gateway image. udts/index.json lists them in import order: a type must come
after every type it nests (its UdtInstance typeIds). Each definition is
imported into [<provider>]_types_/<folder>, overwriting what is there, so the
files are the source of truth and the gateway converges on them.

exportAll writes the gateway's definitions back to the files, normalised
(sorted keys, four-space indent), so a Designer change shows up as a clean diff.
"""

import json
import traceback

from java.lang import Throwable
from system.file import readFileAsString, writeFile
from system.tag import exportTags, importTags
from system.util import getLogger

LOGGER = getLogger("demo.library.udts")

PROJECTS_DIR = "/usr/local/bin/ignition/assets/projects"

MYPY = False
if MYPY:
	from typing import Any, List, Tuple


def udtsDir(
	project,  # type: str
):
	# type: (...) -> str
	"""Return the folder holding a project's UDT files in the gateway image."""
	return "{}/{}/udts".format(PROJECTS_DIR, project)


def definitions(
	project,  # type: str
	index,  # type: List[str]
	provider="default",  # type: str
):
	# type: (...) -> List[Tuple[str, str, str]]
	"""Return (entry, file path, tag folder) for each index entry, in order."""
	result = []  # type: List[Tuple[str, str, str]]
	for entry in index:
		folder, _, name = entry.rpartition("/")
		path = "{}/{}.json".format(udtsDir(project), entry)
		base = (
			"[{}]_types_/{}".format(provider, folder) if folder else "[{}]_types_".format(provider)
		)
		if not name:
			msg = "invalid UDT index entry: {!r}".format(entry)
			raise ValueError(msg)
		result.append((entry, path, base))
	return result


def canonical(
	tag,  # type: Any
	inInstance=False,  # type: bool  # noqa: FBT002 - Jython 2.7 has no keyword-only arguments
):
	# type: (...) -> Any
	"""Return a tag definition without export noise, members sorted by name.

	Exports differ between versions in ways that mean nothing: 8.1 lists every
	member of a nested UdtInstance as a bare {name, tagType} placeholder, and
	the versions order members differently. Placeholders are dropped (a member
	with any override keeps it) and members are sorted, so a definition exports
	to the same file on 8.1 and 8.3.
	"""
	if isinstance(tag, list):
		members = [canonical(t, inInstance) for t in tag]
		members = [
			t
			for t in members
			if not (inInstance and isinstance(t, dict) and set(t) <= {"name", "tagType"})
		]
		return sorted(members, key=lambda t: t.get("name", "") if isinstance(t, dict) else "")
	if isinstance(tag, dict):
		nested = inInstance or tag.get("tagType") == "UdtInstance"
		result = dict(tag)
		if "tags" in result:
			result["tags"] = canonical(result["tags"], nested)
		if nested and result.get("tags") == []:
			del result["tags"]
		return result
	return tag


def normalise(
	text,  # type: str
):
	# type: (...) -> str
	"""Return a tag export in canonical form: no placeholders, sorted, four-space JSON."""
	data = canonical(json.loads(text))  # type: Any
	return json.dumps(data, indent=4, sort_keys=True, separators=(",", ": ")) + "\n"


def readIndex(
	project,  # type: str
):
	# type: (...) -> List[str]
	"""Read a project's udts/index.json."""
	return json.loads(readFileAsString("{}/index.json".format(udtsDir(project))))


def importAll(
	project,  # type: str
	provider="default",  # type: str
):
	# type: (...) -> int
	"""Import a project's UDT definitions in index order; return how many failed."""
	failed = 0
	for entry, path, base in definitions(project, readIndex(project), provider):
		try:
			importTags(path, base, "o")
			LOGGER.debug("[{}] imported {} into {}".format(project, entry, base))
		except (Exception, Throwable) as e:  # noqa: BLE001
			failed += 1
			LOGGER.error(
				"[{}] import of {} failed: {}\n{}".format(project, entry, e, traceback.format_exc())
			)
	if failed:
		LOGGER.warn("[{}] {} UDT definitions failed to import".format(project, failed))
	else:
		LOGGER.info("[{}] UDT definitions imported".format(project))
	return failed


def exportAll(
	project,  # type: str
	provider="default",  # type: str
):
	# type: (...) -> None
	"""Write the gateway's definitions back to the project's UDT files, normalised."""
	for entry, path, base in definitions(project, readIndex(project), provider):
		tagPath = "{}/{}".format(base, entry.rpartition("/")[2])
		exportTags(path, [tagPath])
		writeFile(path, normalise(readFileAsString(path)))
		LOGGER.debug("[{}] exported {} to {}".format(project, tagPath, path))
