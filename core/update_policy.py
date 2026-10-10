"""Desktop update monitoring policy (checks only, never silent installs)."""
from __future__ import annotations

from .updater import version_tuple

# Public GitHub API without credentials allows 60 requests/hour per IP.
# Five-minute checks are prompt without exhausting typical public rate limits.
AUTO_UPDATE_INTERVAL_MS = 5 * 60 * 1000
STARTUP_DELAY_MS = 1500


def should_show_update(version: str, notified_version: str | None, *, manual: bool = False) -> bool:
    """A release notifies once per open session; manual checks can reopen it."""
    version_tuple(version)  # Validate rather than trusting arbitrary release tags.
    return bool(manual or version != notified_version)
