"""Domain events published by services and consumed by observers."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums import EventType


@dataclass
class DomainEvent:
    type: EventType
    description: str
    occurred_at: datetime
    actor_id: int | None = None
    incident: Any = None  # the Incident entity (kept loose to keep the domain free of ORM imports)
    previous_state: str | None = None
    new_state: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def incident_id(self) -> int | None:
        return getattr(self.incident, "id", None)
