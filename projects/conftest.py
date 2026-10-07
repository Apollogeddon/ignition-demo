"""Stand in for the gateway's scripting modules so project scripts import in CPython.

Scripts import straight from system.* (from system.util import getLogger), so the
modules must exist before any script is imported: they are mocks registered here,
at collection time, and reset before each test.
"""

import builtins
import sys
from unittest.mock import MagicMock

import pytest

# Jython 2.7 names the scripts may use
builtins.unicode = str  # type: ignore[attr-defined]
builtins.basestring = str  # type: ignore[attr-defined]

SYSTEM_MODULES = (
	"system",
	"system.dataset",
	"system.file",
	"system.date",
	"system.db",
	"system.perspective",
	"system.tag",
	"system.user",
	"system.util",
)
MOCKS = {name: MagicMock(name=name) for name in SYSTEM_MODULES}
sys.modules.update(MOCKS)


class Throwable(Exception):  # noqa: N818
	"""Stand-in for java.lang.Throwable, so except (Exception, Throwable) works."""


java = MagicMock(name="java")
java.lang.Throwable = Throwable
sys.modules.update({"java": java, "java.lang": java.lang})


@pytest.fixture(autouse=True)
def _reset_system() -> None:
	"""Forget calls and return values from earlier tests."""
	for mock in MOCKS.values():
		mock.reset_mock(return_value=True, side_effect=True)


@pytest.fixture
def system_util() -> MagicMock:
	"""Return the mocked system.util module."""
	return MOCKS["system.util"]
