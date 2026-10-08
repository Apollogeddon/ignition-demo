"""Seed an Ignition 8.1 gateway's configuration from a spec file.

8.3 is configured through its REST API (OpenTofu, cluster/modules/gateway-config);
8.1 has no such API, so the startup event applies a spec instead: the
gateway/seed/seed.json shipped in the image. Each item is created only if it
is missing, so a fresh gateway is seeded and later changes made in the
gateway are kept, as a first-boot backup restore would.

Values may use ${NAME} or ${NAME:-default} for environment variables, so the
same spec serves every environment and secrets stay out of it. An item that
needs a variable with no value is skipped and logged.

Sections (each a map of name to item, applied in this order):

    securityLevels      top-level security level trees: {description, children}
    databases           {driver, url, user, password}
    userSources         {type, profile, settings, roles, users: [{name, password, roles}]}
    identityProviders   {userSource, description}: an Ignition IdP using that user source
    alarmJournals       {type, profile, settings}
    auditProfiles       {type, profile, settings}
    emailProfiles       {type, profile, settings}: SMTP profiles
    alarmNotificationProfiles  {type, profile, settings}: Alarm Notification module
    gateway             {auditProfile}: system settings

profile and settings hold record fields by name; a value naming another
record (e.g. "Datasource": "demo") is looked up by that record's name.
"""

import json
import os
import re

from java.lang import Throwable

MYPY = False
if MYPY:
	from typing import Any, Callable, Dict, List, Optional, Tuple

LOGGER_NAME = "demo.library.seed"
SPEC_FILE = "/usr/local/bin/ignition/assets/seed/seed.json"

SECTIONS = (
	"securityLevels",
	"databases",
	"userSources",
	"identityProviders",
	"alarmJournals",
	"auditProfiles",
	"emailProfiles",
	"alarmNotificationProfiles",
	"gateway",
)

# Jython 2.7 reads JSON strings as unicode; CPython has only str
try:
	STRING_TYPES = (str, unicode)  # type: ignore[name-defined]
except NameError:
	STRING_TYPES = (str,)

PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class MissingVariable(Exception):  # noqa: N818
	"""A ${NAME} placeholder has no value and no default."""


def resolve(
	value,  # type: Any
	getenv,  # type: Callable[[str], Optional[str]]
):
	# type: (...) -> Any
	"""Return value with every ${NAME} / ${NAME:-default} replaced, recursively."""
	if isinstance(value, dict):
		return {key: resolve(item, getenv) for key, item in value.items()}
	if isinstance(value, list):
		return [resolve(item, getenv) for item in value]
	if not isinstance(value, STRING_TYPES):
		return value

	def replace(match):
		# type: (Any) -> str
		name, default = match.group(1), match.group(2)
		found = getenv(name)
		if found:
			return found
		if default is not None:
			return default
		raise MissingVariable(name)

	return PLACEHOLDER.sub(replace, value)


def loadSpec(
	path=SPEC_FILE,  # type: str
):
	# type: (...) -> Dict[str, Any]
	"""Read a seed spec; a missing file is an empty spec."""
	if not os.path.isfile(path):
		return {}
	with open(path) as f:
		spec = json.load(f)
	unknown = [key for key in spec if key not in SECTIONS and not key.startswith("$")]
	if unknown:
		msg = "unknown seed sections: {}".format(", ".join(sorted(unknown)))
		raise ValueError(msg)
	return spec


def apply(
	spec,  # type: Dict[str, Any]
	gateway,  # type: Any
	log,  # type: Any
	getenv=os.getenv,  # type: Callable[[str], Optional[str]]
):
	# type: (...) -> Dict[str, List[str]]
	"""Create every item of the spec the gateway does not have yet.

	gateway is an adapter (Gateway81 on a real gateway). Returns the names
	created, skipped (missing variables) and failed, as "section/name".
	"""
	result = {"created": [], "skipped": [], "failed": []}  # type: Dict[str, List[str]]
	for section in SECTIONS:
		items = spec.get(section) or {}
		if section == "gateway":
			items = {"settings": items} if items else {}
		existing = set(gateway.existing(section))
		for name in sorted(items):
			key = "{}/{}".format(section, name)
			if section != "gateway" and name in existing:
				log.debug("Seed: {} exists".format(key))
				continue
			try:
				item = resolve(items[name], getenv)
			except MissingVariable as e:
				log.warn("Seed: {} skipped, ${{{}}} is not set".format(key, e.args[0]))
				result["skipped"].append(key)
				continue
			try:
				if gateway.create(section, name, item) is False:
					log.debug("Seed: {} unchanged".format(key))
					continue
				result["created"].append(key)
				log.debug("Seed: {} created".format(key))
			except (Exception, Throwable) as e:  # noqa: BLE001
				log.error("Seed: {} failed: {}".format(key, e))
				result["failed"].append(key)
	if result["created"] or result["failed"]:
		log.info(
			"Seed: created {}{}".format(
				", ".join(result["created"]) or "nothing",
				"; failed {}".format(", ".join(result["failed"])) if result["failed"] else "",
			)
		)
	return result


def applyFile(
	path=SPEC_FILE,  # type: str
):
	# type: (...) -> Optional[Dict[str, List[str]]]
	"""Apply the image's seed spec on 8.1; do nothing on gateways with a REST API."""
	from system.util import getLogger, getVersion

	log = getLogger(LOGGER_NAME)
	version = getVersion()
	if (version.getMajor(), version.getMinor()) >= (8, 3):
		log.debug("Gateway configured through its REST API; seed not applied")
		return None
	spec = loadSpec(path)
	if not spec:
		log.debug("No seed spec at {}".format(path))
		return None
	from library.gateway81 import Gateway81

	return apply(spec, Gateway81(), log)
