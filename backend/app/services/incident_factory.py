"""Factory that builds fully initialised Incident entities."""
from uuid import uuid4

from app.domain.enums import IncidentStatus
from app.models import Incident


class IncidentFactory:
    NUMBER_PREFIX = "INC-"
    NUMBER_OFFSET = 1000

    @staticmethod
    def create(*, title, description, reporter, service, category, category_source, impact, urgency,
               criticality, criticality_overridden, priority_result, affected_system, affected_users,
               now, effective_impact=None) -> Incident:
        return Incident(
            number=f"TMP-{uuid4().hex[:20]}",  # replaced by `assign_number` after the first flush
            title=title.strip(), description=description.strip(),
            reporter=reporter, reporter_id=reporter.id,
            category=category, category_id=category.id if category else None,
            category_source=category_source,
            service=service, service_id=service.id,
            affected_system=(affected_system or None), affected_users=affected_users,
            impact=impact, effective_impact=effective_impact or impact, urgency=urgency,
            business_criticality=criticality,
            criticality_overridden=criticality_overridden,
            priority_score=priority_result.score, priority=priority_result.priority,
            status=IncidentStatus.NEW, created_at=now, updated_at=now,
        )

    @classmethod
    def assign_number(cls, incident: Incident) -> None:
        incident.number = f"{cls.NUMBER_PREFIX}{cls.NUMBER_OFFSET + incident.id}"
