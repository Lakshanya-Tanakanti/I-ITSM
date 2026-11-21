from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.enums import (
    DONE_STATUSES, OPEN_STATUSES, IncidentStatus, Priority, SlaStatus, SlaType, NoteType,
)
from app.models import (
    EmployeeFeedback, Incident, InvestigationNote, Resolution, SlaViolation,
)
from app.repositories.base import BaseRepository


@dataclass
class IncidentFilters:
    number: Optional[str] = None
    q: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    statuses: list = field(default_factory=list)
    priorities: list = field(default_factory=list)
    category_id: Optional[int] = None
    service_id: Optional[int] = None
    technician_id: Optional[int] = None
    sla_statuses: list = field(default_factory=list)
    reporter_id: Optional[int] = None  # visibility scope for employees
    scope_technician_id: Optional[int] = None  # visibility scope for technicians
    unassigned: bool = False
    awaiting_info: Optional[bool] = None
    sort: str = "-created_at"
    page: int = 1
    page_size: int = 20


SORT_COLUMNS = {
    "created_at": Incident.created_at,
    "updated_at": Incident.updated_at,
    "number": Incident.number,
    "priority": Incident.priority_score,
    "status": Incident.status,
    "sla_status": Incident.sla_status,
    "title": Incident.title,
    "resolution_deadline": Incident.resolution_deadline,
}


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    _LIST_OPTIONS = (
        joinedload(Incident.reporter), joinedload(Incident.service),
        joinedload(Incident.category), joinedload(Incident.assigned_technician),
    )

    def get_by_number(self, number: str) -> Optional[Incident]:
        return self.session.scalar(
            select(Incident).where(func.upper(Incident.number) == number.strip().upper())
        )

    def search(self, f: IncidentFilters) -> tuple:
        conds = []
        if f.number:
            conds.append(func.upper(Incident.number).like(f"%{f.number.strip().upper()}%"))
        if f.q:
            like = f"%{f.q.strip().lower()}%"
            conds.append(or_(func.lower(Incident.title).like(like),
                             func.lower(Incident.description).like(like),
                             func.lower(Incident.number).like(like)))
        if f.from_date:
            conds.append(Incident.created_at >= datetime.combine(f.from_date, datetime.min.time()))
        if f.to_date:
            conds.append(Incident.created_at < datetime.combine(f.to_date + timedelta(days=1), datetime.min.time()))
        if f.statuses:
            conds.append(Incident.status.in_(f.statuses))
        if f.priorities:
            conds.append(Incident.priority.in_(f.priorities))
        if f.category_id:
            conds.append(Incident.category_id == f.category_id)
        if f.service_id:
            conds.append(Incident.service_id == f.service_id)
        if f.technician_id:
            conds.append(Incident.assigned_technician_id == f.technician_id)
        if f.unassigned:
            conds.append(Incident.assigned_technician_id.is_(None))
            conds.append(Incident.status.in_(OPEN_STATUSES))
        if f.sla_statuses:
            conds.append(Incident.sla_status.in_(f.sla_statuses))
        if f.awaiting_info is not None:
            conds.append(Incident.awaiting_info.is_(f.awaiting_info))
        if f.reporter_id:
            conds.append(Incident.reporter_id == f.reporter_id)
        if f.scope_technician_id:
            conds.append(Incident.assigned_technician_id == f.scope_technician_id)

        where = and_(*conds) if conds else None
        count_stmt = select(func.count(Incident.id))
        if where is not None:
            count_stmt = count_stmt.where(where)
        total = self.session.scalar(count_stmt) or 0

        sort_key = f.sort or "-created_at"
        desc = sort_key.startswith("-")
        column = SORT_COLUMNS.get(sort_key.lstrip("-+"), Incident.created_at)
        order = column.desc() if desc else column.asc()

        stmt = select(Incident).options(*self._LIST_OPTIONS)
        if where is not None:
            stmt = stmt.where(where)
        stmt = stmt.order_by(order, Incident.id.desc()).offset((f.page - 1) * f.page_size).limit(f.page_size)
        items = list(self.session.scalars(stmt).unique().all())
        return items, total

    def list_open(self) -> list:
        return list(self.session.scalars(
            select(Incident).where(Incident.status.in_(OPEN_STATUSES)).options(*self._LIST_OPTIONS)
        ).unique().all())

    def recent(self, since: datetime, exclude_id: Optional[int] = None, limit: int = 500) -> list:
        stmt = select(Incident).where(Incident.created_at >= since)
        if exclude_id is not None:
            stmt = stmt.where(Incident.id != exclude_id)
        stmt = stmt.order_by(Incident.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def resolved_with_resolution(self, category_id: Optional[int], service_id: int, exclude_id: int,
                                 limit: int = 200) -> list:
        conds = [Incident.id != exclude_id, Incident.status.in_(DONE_STATUSES)]
        scope = [Incident.service_id == service_id]
        if category_id:
            scope.append(Incident.category_id == category_id)
        conds.append(or_(*scope))
        return list(self.session.scalars(
            select(Incident).join(Resolution, Resolution.incident_id == Incident.id)
            .where(*conds).order_by(Incident.resolved_at.desc()).limit(limit)
        ).all())

    def open_for_service(self, service_id: int, exclude_id: int, since: datetime) -> list:
        return list(self.session.scalars(
            select(Incident).where(Incident.service_id == service_id, Incident.id != exclude_id,
                                   Incident.created_at >= since)
            .options(*self._LIST_OPTIONS).order_by(Incident.created_at.desc())
        ).unique().all())

    def count(self) -> int:
        return self.session.scalar(select(func.count(Incident.id))) or 0


class NoteRepository(BaseRepository[InvestigationNote]):
    model = InvestigationNote

    def for_incident(self, incident_id: int, include_internal: bool) -> list:
        stmt = (select(InvestigationNote).where(InvestigationNote.incident_id == incident_id)
                .options(joinedload(InvestigationNote.author))
                .order_by(InvestigationNote.created_at, InvestigationNote.id))
        if not include_internal:
            stmt = stmt.where(InvestigationNote.is_internal.is_(False))
        return list(self.session.scalars(stmt).unique().all())

    def last_of_type(self, incident_id: int, note_type: NoteType) -> Optional[InvestigationNote]:
        return self.session.scalar(
            select(InvestigationNote)
            .where(InvestigationNote.incident_id == incident_id, InvestigationNote.note_type == note_type)
            .order_by(InvestigationNote.id.desc()).limit(1)
        )


class ResolutionRepository(BaseRepository[Resolution]):
    model = Resolution

    def get_for_incident(self, incident_id: int) -> Optional[Resolution]:
        return self.session.scalar(select(Resolution).where(Resolution.incident_id == incident_id))


class FeedbackRepository(BaseRepository[EmployeeFeedback]):
    model = EmployeeFeedback

    def get_for_incident(self, incident_id: int) -> Optional[EmployeeFeedback]:
        return self.session.scalar(select(EmployeeFeedback).where(EmployeeFeedback.incident_id == incident_id))

    def average_rating(self) -> Optional[float]:
        return self.session.scalar(select(func.avg(EmployeeFeedback.rating)))


class SlaViolationRepository(BaseRepository[SlaViolation]):
    model = SlaViolation

    def exists(self, incident_id: int, sla_type: SlaType) -> bool:
        return self.session.scalar(
            select(func.count(SlaViolation.id)).where(
                SlaViolation.incident_id == incident_id, SlaViolation.sla_type == sla_type)
        ) > 0

    def list_all(self, limit: int = 200) -> list:
        return list(self.session.scalars(
            select(SlaViolation).options(joinedload(SlaViolation.incident).joinedload(Incident.service),
                                         joinedload(SlaViolation.incident).joinedload(Incident.assigned_technician))
            .order_by(SlaViolation.detected_at.desc()).limit(limit)
        ).unique().all())

    def count(self) -> int:
        return self.session.scalar(select(func.count(SlaViolation.id))) or 0
