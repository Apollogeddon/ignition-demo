"""Gateway event entry points (called from the project's gateway events).

The event scripts themselves are one line each, the same on 8.1 and 8.3, and
everything they do lives here where it can be tested.
"""

import traceback

from java.lang import Throwable
from library.udts import exportAll, importAll
from project.assets import syncInstances
from system.util import getLogger

LOGGER = getLogger("demo.project.gateway")

UDT_PROJECTS = ("library",)

MYPY = False
if MYPY:
	from typing import Any


def onStartup():
	# type: (...) -> None
	"""Import the UDT definitions, then create an instance per asset."""
	for project in UDT_PROJECTS:
		importAll(project)
	try:
		syncInstances()
	except (Exception, Throwable) as e:  # noqa: BLE001
		# expected until the demo database connection exists (gateway-config)
		LOGGER.warn("Asset instances not synchronised: {}".format(e))
		LOGGER.debug(traceback.format_exc())


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
