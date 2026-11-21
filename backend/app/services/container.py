"""Dependency wiring. One container per database session (per request)."""
from dataclasses import dataclass

from app.config import Settings
from app.observers.audit_observer import AuditObserver
from app.observers.base import EventBus
from app.observers.notification_observer import NotificationObserver
from app.repositories import Repositories
from app.services.assignment_service import AssignmentService
from app.services.auth_service import AuthService
from app.services.config_service import ConfigService
from app.services.incident_service import IncidentService
from app.services.intelligence_service import IntelligenceService
from app.services.notification_service import NotificationService
from app.services.presenter import IncidentPresenter
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService
from app.services.sla_service import SlaService
from app.services.user_service import UserService


@dataclass
class Container:
    session: object
    clock: object
    repos: Repositories
    bus: EventBus
    settings: SettingsService
    sla: SlaService
    assignment: AssignmentService
    intelligence: IntelligenceService
    incidents: IncidentService
    presenter: IncidentPresenter
    auth: AuthService
    users: UserService
    config: ConfigService
    notifications: NotificationService
    reports: ReportService


def build_container(session, clock, app_settings: Settings) -> Container:
    repos = Repositories.for_session(session)
    bus = EventBus()
    # Observer pattern: audit and notifications react to every published event.
    bus.subscribe(AuditObserver(repos.audit))
    bus.subscribe(NotificationObserver(repos, clock))

    settings = SettingsService(session, repos, bus, clock, app_settings)
    sla = SlaService(session, repos, bus, clock, settings)
    assignment = AssignmentService(repos, settings)
    intelligence = IntelligenceService(repos, clock, settings, sla)
    incidents = IncidentService(session, repos, bus, clock, settings, sla, assignment, intelligence)
    presenter = IncidentPresenter(repos, sla, intelligence, incidents)
    users = UserService(session, repos, bus, clock, settings)
    reports = ReportService(session, repos, clock, sla, users, presenter)
    return Container(
        session=session, clock=clock, repos=repos, bus=bus, settings=settings, sla=sla,
        assignment=assignment, intelligence=intelligence, incidents=incidents, presenter=presenter,
        auth=AuthService(session, repos, bus, clock, settings), users=users,
        config=ConfigService(session, repos, bus, clock), notifications=NotificationService(session, repos, bus, clock),
        reports=reports,
    )
