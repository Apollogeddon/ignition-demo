"""Tests for library.format."""

import pytest
from library.format.code import duration, percent


@pytest.mark.parametrize(
	("seconds", "text"),
	[
		(-5, "0s"),
		(12, "12s"),
		(249, "4m 09s"),
		(3900, "1h 05m"),
		(183600, "2d 3h"),
	],
)
def test_duration(seconds: float, text: str) -> None:
	assert duration(seconds) == text


def test_percent() -> None:
	assert percent(0.256) == "26%"
	assert percent(0.256, 1) == "25.6%"
	assert percent(None) == "—"
