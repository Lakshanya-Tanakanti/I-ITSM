"""Injectable clock. All timestamps are timezone-aware UTC datetimes."""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC time (timezone aware)."""


class SystemClock(Clock):
    def now(self) -> datetime:
        return utcnow()


class MutableClock(Clock):
    """A clock that can be moved by hand. Used by tests and by the seeder."""

    def __init__(self, start: datetime | None = None):
        self._now = (start or utcnow())
        if self._now.tzinfo is None:
            self._now = self._now.replace(tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def set(self, value: datetime) -> None:
        self._now = value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def advance(self, **kwargs) -> datetime:
        self._now = self._now + timedelta(**kwargs)
        return self._now
