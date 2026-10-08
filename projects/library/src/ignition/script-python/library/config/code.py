"""Gateway configuration that 8.1 can only get from scripts.

On 8.3, gateway resources such as database connections are configured
through the REST API by OpenTofu (cluster/modules/gateway-config), and this
module does nothing. 8.1 has no such API, so on 8.1 the startup event creates
the connections the deployment describes in environment variables:

    GATEWAY_DB_<NAME>_URL        JDBC URL (required; the connection is skipped without it)
    GATEWAY_DB_<NAME>_USER
    GATEWAY_DB_<NAME>_PASSWORD
    GATEWAY_DB_<NAME>_DRIVER     JDBC driver name (default PostgreSQL)

A connection that already exists is left alone: the environment creates it,
and later changes are made in the gateway (or by redeploying a fresh volume).
"""

import os

from library.data import toRows
from system.db import addDatasource, getConnections
from system.util import getLogger, getVersion

LOGGER = getLogger("demo.library.config")

MYPY = False
if MYPY:
	from typing import Callable, Optional


def configuredByApi():
	# type: (...) -> bool
	"""Return whether this gateway is configured through the REST API (8.3 and later)."""
	version = getVersion()
	return (version.getMajor(), version.getMinor()) >= (8, 3)


def ensureDatasource(
	name,  # type: str
	getenv=os.getenv,  # type: Callable[[str], Optional[str]]
):
	# type: (...) -> bool
	"""Create database connection <name> from the environment if it is missing (8.1).

	Return whether a connection was created.
	"""
	if configuredByApi():
		LOGGER.debug("Gateway configured through its REST API; not creating {}".format(name))
		return False
	prefix = "GATEWAY_DB_{}_".format(name.upper())
	url = getenv(prefix + "URL")
	if not url:
		LOGGER.debug("{}URL not set; not creating {}".format(prefix, name))
		return False
	existing = [str(row["Name"]) for row in toRows(getConnections())]
	if name in existing:
		LOGGER.debug("Database connection {} already exists".format(name))
		return False
	addDatasource(
		getenv(prefix + "DRIVER") or "PostgreSQL",
		name,
		"Created from the environment by the gateway startup event",
		url,
		getenv(prefix + "USER"),
		getenv(prefix + "PASSWORD"),
	)
	LOGGER.info("Created database connection {} ({})".format(name, url))
	return True
