"""Observer pattern: the event bus (subject) and the observer contract."""
import logging
from abc import ABC, abstractmethod

from sqlalchemy.exc import SQLAlchemyError

from app.domain.events import DomainEvent

logger = logging.getLogger("iitsm.events")


class EventObserver(ABC):
    """Reacts to domain events. Observers never drive the incident workflow."""

    #: A critical observer (audit) aborts the transaction if it fails.
    critical: bool = False

    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """React to one event."""


class EventBus:
    """Subject. Services publish events; subscribed observers react."""

    def __init__(self) -> None:
        self._observers: list = []

    def subscribe(self, observer: EventObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: EventObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    @property
    def observers(self) -> list:
        return list(self._observers)

    def publish(self, event: DomainEvent) -> None:
        for observer in self._observers:
            try:
                observer.handle(event)
            except SQLAlchemyError:
                raise  # database trouble must never be swallowed
            except Exception:  # noqa: BLE001
                if observer.critical:
                    raise
                logger.exception("Observer %s failed for %s", type(observer).__name__, event.type.value)
