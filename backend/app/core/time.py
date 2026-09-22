"""Single place for the timezone-aware "now" used across persisted records."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
