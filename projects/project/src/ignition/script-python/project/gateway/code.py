"""Gateway event entry points (called from the project's gateway events).

The event scripts themselves are one line each, the same on 8.1 and 8.3, and
everything they do lives here where it can be tested.
"""

import time
import traceback

from java.lang import Throwable
from library.seed import applyFile
from library.udts import exportAll, importAll
from project.assets import syncInstances
from system.util import getLogger, invokeAsynchronous

LOGGER = getLogger("demo.project.gateway")

UDT_PROJECTS = ("library",)

# a database connection the seed has just created takes a few seconds to come up
SYNC_ATTEMPTS = 12
SYNC_DELAY_SECONDS = 5

MYPY = False
if MYPY:
	from typing import Any


def onStartup():
	# type: (...) -> None
	"""Seed the gateway (8.1), import the UDT definitions, then create an instance per asset.

	On 8.1 the gateway configuration (database connection, journal, users, ...)
	comes from the image's seed spec; 8.3 gets it from OpenTofu through the REST
	API and the seed does nothing.
	"""
	try:
		applyFile()
	except (Exception, Throwable) as e:  # noqa: BLE001
		LOGGER.error("Gateway seed not applied: {}".format(e))
		LOGGER.debug(traceback.format_exc())
	for project in UDT_PROJECTS:
		importAll(project)
	# in the background, so the gateway's startup is not held up by the retries
	invokeAsynchronous(syncWhenReady)


def syncWhenReady(
	attempts=SYNC_ATTEMPTS,  # type: int
	delay=SYNC_DELAY_SECONDS,  # type: float
):
	# type: (...) -> bool
	"""Synchronise the asset instances, retrying while the database comes up."""
	for attempt in range(1, attempts + 1):
		try:
			syncInstances()
		except (Exception, Throwable) as e:  # noqa: BLE001
			if attempt == attempts:
				# on 8.3, expected until gateway-config creates the connection
				LOGGER.warn("Asset instances not synchronised: {}".format(e))
				LOGGER.debug(traceback.format_exc())
				return False
			LOGGER.debug("Asset sync attempt {} failed: {}".format(attempt, e))
			time.sleep(delay)
		else:
			return True
	return False


def onUpdate(
	actor,  # type: Any
	resources,  # type: Any  # noqa: ARG001 - Ignition passes it
):
	# type: (...) -> None
	"""Write the UDT definitions back to the project files after a project save.

	In develop, where the project folders are mounted, this turns UDT edits made
	in the Designer into file changes to commit (save the project after editing
	tags). Elsewhere the files are the image's and the write is harmless.
	"""
	LOGGER.debug("Project updated by {}; exporting UDT definitions".format(actor))
	for project in UDT_PROJECTS:
		try:
			exportAll(project)
		except (Exception, Throwable) as e:  # noqa: BLE001
			LOGGER.warn("UDT export for {} failed: {}".format(project, e))
