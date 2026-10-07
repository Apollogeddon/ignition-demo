"""Formatting helpers shared by every project."""

import sys

if sys.version_info.major >= 3:
	from typing import Optional


def duration(
	seconds,  # type: float
):
	# type: (...) -> str
	"""Format a number of seconds as e.g. "2d 3h", "1h 05m", "4m 09s" or "12s"."""
	total = int(max(seconds, 0))
	days, rest = divmod(total, 86400)
	hours, rest = divmod(rest, 3600)
	minutes, secs = divmod(rest, 60)
	if days:
		return "{}d {}h".format(days, hours)
	if hours:
		return "{}h {:02d}m".format(hours, minutes)
	if minutes:
		return "{}m {:02d}s".format(minutes, secs)
	return "{}s".format(secs)


def percent(
	value,  # type: Optional[float]
	digits=0,  # type: int
):
	# type: (...) -> str
	"""Format a 0-1 ratio as a percentage, or an em dash when it is unknown."""
	if value is None:
		return "—"
	return "{:.{}f}%".format(value * 100, digits)
