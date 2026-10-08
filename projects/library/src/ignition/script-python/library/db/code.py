"""Database helpers that work on Ignition 8.1 and 8.3.

8.3 runs named queries with system.db.execQuery; 8.1 only has runNamedQuery.
Scripts call library.db.namedQuery and get whichever the gateway provides.
"""

# each import only exists in one version's stubs, hence the pyright ignores
try:
	# Ignition 8.3
	from system.db import execQuery as _runNamedQuery  # pyright: ignore[reportAttributeAccessIssue]
except ImportError:
	# Ignition 8.1
	from system.db import (
		runNamedQuery as _runNamedQuery,  # pyright: ignore[reportAttributeAccessIssue]
	)

MYPY = False
if MYPY:
	from typing import Any, Dict, Optional


def namedQuery(
	path,  # type: str
	params=None,  # type: Optional[Dict[str, Any]]
):
	# type: (...) -> Any
	"""Run a named query of the current project and return its result."""
	return _runNamedQuery(path, params or {})
