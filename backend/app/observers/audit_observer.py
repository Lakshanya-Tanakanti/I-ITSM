import json

from app.domain.events import DomainEvent
from app.models import AuditLog
from app.observers.base import EventObserver
from app.repositories.notification_repository import AuditRepository


class AuditObserver(EventObserver):
    """Writes one append-only audit row for every domain event."""

    critical = True

    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo

    def handle(self, event: DomainEvent) -> None:
        extra = json.dumps(event.metadata, default=str) if event.metadata else None
        self.audit_repo.append(
            AuditLog(
                actor_id=event.actor_id,
                incident_id=event.incident_id,
                action=event.type.value,
                previous_state=event.previous_state,
                new_state=event.new_state,
                description=event.description,
                extra=extra,
                created_at=event.occurred_at,
            )
        )
