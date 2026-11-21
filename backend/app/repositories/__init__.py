from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.config_repository import (
    CategoryRepository, ServiceRepository, SettingRepository, SlaPolicyRepository,
)
from app.repositories.incident_repository import (
    FeedbackRepository, IncidentFilters, IncidentRepository, NoteRepository, ResolutionRepository,
    SlaViolationRepository,
)
from app.repositories.notification_repository import AuditRepository, NotificationRepository
from app.repositories.user_repository import TeamRepository, TechnicianRepository, UserRepository


@dataclass
class Repositories:
    """Bundle of every repository bound to one database session."""

    users: UserRepository
    teams: TeamRepository
    technicians: TechnicianRepository
    categories: CategoryRepository
    services: ServiceRepository
    sla_policies: SlaPolicyRepository
    settings: SettingRepository
    incidents: IncidentRepository
    notes: NoteRepository
    resolutions: ResolutionRepository
    feedback: FeedbackRepository
    violations: SlaViolationRepository
    notifications: NotificationRepository
    audit: AuditRepository

    @classmethod
    def for_session(cls, session: Session) -> "Repositories":
        return cls(
            users=UserRepository(session), teams=TeamRepository(session),
            technicians=TechnicianRepository(session), categories=CategoryRepository(session),
            services=ServiceRepository(session), sla_policies=SlaPolicyRepository(session),
            settings=SettingRepository(session), incidents=IncidentRepository(session),
            notes=NoteRepository(session), resolutions=ResolutionRepository(session),
            feedback=FeedbackRepository(session), violations=SlaViolationRepository(session),
            notifications=NotificationRepository(session), audit=AuditRepository(session),
        )


__all__ = ["Repositories", "IncidentFilters"]
