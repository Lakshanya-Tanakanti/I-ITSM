"""Shared service plumbing: transactions and event emission."""
from functools import wraps
from typing import Optional

from app.domain.events import DomainEvent


def transactional(fn):
    """Run a service method as one database transaction.

    The outermost call commits, or rolls everything back if anything fails
    (NFR: one transaction per multi-step workflow).
    """

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        session = self.session
        depth = session.info.get("tx_depth", 0)
        session.info["tx_depth"] = depth + 1
        try:
            result = fn(self, *args, **kwargs)
            if depth == 0:
                session.commit()
            return result
        except Exception:
            if depth == 0:
                session.rollback()
            raise
        finally:
            session.info["tx_depth"] = depth

    return wrapper


class BaseService:
    def __init__(self, session, repos, bus, clock):
        self.session = session
        self.repos = repos
        self.bus = bus
        self.clock = clock

    def emit(self, event_type, description: str, *, incident=None, actor=None,
             previous_state: Optional[str] = None, new_state: Optional[str] = None, **metadata) -> None:
        self.bus.publish(DomainEvent(
            type=event_type, description=description, occurred_at=self.clock.now(),
            actor_id=getattr(actor, "id", actor), incident=incident,
            previous_state=previous_state, new_state=new_state, metadata=metadata,
        ))
