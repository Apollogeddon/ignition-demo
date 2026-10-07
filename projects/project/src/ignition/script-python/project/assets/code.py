"""Asset queries and summaries for the overview views."""

from library.data import toRows
from system.db import execQuery
from system.tag import configure
from system.util import getLogger

LOGGER = getLogger("demo.project.assets")

MYPY = False
if MYPY:
	from typing import Any, Dict, Iterable, List


def summarise(
	rows,  # type: Iterable[Dict[str, Any]]
):
	# type: (...) -> List[Dict[str, Any]]
	"""Count assets per area, largest first, then by area name."""
	counts = {}  # type: Dict[str, int]
	for row in rows:
		area = row["area"] or "Unassigned"
		counts[area] = counts.get(area, 0) + 1
	ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
	return [{"area": area, "count": count} for area, count in ordered]


def getSummary():
	# type: (...) -> List[Dict[str, Any]]
	"""Run the assets/list named query and summarise it per area."""
	summary = summarise(toRows(execQuery("assets/list", {})))
	LOGGER.debug("Summarised {} areas".format(len(summary)))
	return summary


def buildInstances(
	rows,  # type: Iterable[Dict[str, Any]]
	kinds,  # type: Iterable[str]
):
	# type: (...) -> Dict[str, List[Dict[str, Any]]]
	"""Group one UDT instance per asset by area folder.

	An asset's kind names its UDT, equipment/<kind>. Assets whose kind has no
	definition are skipped and logged, so one bad row does not stop the rest.
	"""
	known = set(kinds)
	folders = {}  # type: Dict[str, List[Dict[str, Any]]]
	for row in rows:
		if row["kind"] not in known:
			LOGGER.warn(
				"Asset {} has kind {} with no UDT; skipped".format(row["name"], row["kind"])
			)
			continue
		folder = row["area"] or "Unassigned"
		folders.setdefault(folder, []).append(
			{
				"name": row["name"],
				"tagType": "UdtInstance",
				"typeId": "equipment/{}".format(row["kind"]),
			}
		)
	return folders


def syncInstances(
	provider="default",  # type: str
	kinds=("pump", "blower", "mixer", "level"),  # type: Iterable[str]
):
	# type: (...) -> int
	"""Create or update a UDT instance for every enabled asset; return how many.

	Instances are merged ("m"), so values and overrides set on existing
	instances are kept. Instances of removed assets are left for review.
	"""
	folders = buildInstances(toRows(execQuery("assets/list", {})), kinds)
	for folder, tags in sorted(folders.items()):
		configure("[{}]Assets/{}".format(provider, folder), tags, "m")
	count = sum(len(tags) for tags in folders.values())
	LOGGER.info("Synchronised {} asset instances in {} areas".format(count, len(folders)))
	return count
