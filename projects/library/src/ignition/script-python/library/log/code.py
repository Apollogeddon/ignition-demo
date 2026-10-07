"""Loggers named consistently across projects (library.log).

Use DEBUG for routine progress and INFO only for events worth noticing, so the
gateway log stays useful on small disks.
"""

from system.util import getLogger

PREFIX = "demo"


def get(
	name,  # type: str
):
	# type: (...) -> object
	"""Return the gateway logger "demo.<name>"."""
	return getLogger("{}.{}".format(PREFIX, name))
