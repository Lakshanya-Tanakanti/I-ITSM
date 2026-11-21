"""Reports and role specific dashboards. Every number comes from database queries."""
from collections import defaultdict
from datetime import timedelta
from typing import Optional

from sqlalchemy import func, select

from app.domain.enums import (
    DONE_STATUSES, OPEN_STATUSES, IncidentStatus, Priority, Role, SlaStatus,
)
from app.models import (
    AuditLog, Incident, IncidentCategory, Notification, Service, SlaViolation,
)


class ReportService:
    def __init__(self, session, repos, clock, sla_service, user_service, presenter):
        self.session = session
        self.repos = repos
        self.clock = clock
        self.sla = sla_service
        self.users = user_service
        self.presenter = presenter

    # ------------------------------------------------------------------ helpers
    def _count(self, *conds) -> int:
        stmt = select(func.count(Incident.id))
        for c in conds:
            stmt = stmt.where(c)
        return self.session.scalar(stmt) or 0

    # ------------------------------------------------------------------ reports
    def overview(self) -> dict:
        total = self._count()
        open_ = self._count(Incident.status.in_(OPEN_STATUSES))
        resolved = self._count(Incident.status.in_(DONE_STATUSES))
        critical_open = self._count(Incident.priority == Priority.P1, Incident.status.in_(OPEN_STATUSES))
        critical_total = self._count(Incident.priority == Priority.P1)
        by_priority = {p.value: self._count(Incident.priority == p) for p in Priority}
        by_status = {s.value: self._count(Incident.status == s) for s in IncidentStatus}
        done_breached = self.session.scalar(
            select(func.count(func.distinct(SlaViolation.incident_id)))
            .join(Incident, Incident.id == SlaViolation.incident_id)
            .where(Incident.status.in_(DONE_STATUSES))) or 0
        compliance = round((resolved - done_breached) / resolved * 100, 1) if resolved else None
        resolved_rows = self.session.execute(
            select(Incident.created_at, Incident.resolved_at).where(Incident.resolved_at.is_not(None),
                                                                    Incident.status.in_(DONE_STATUSES))).all()
        avg_minutes = (sum((r - c).total_seconds() for c, r in resolved_rows) / len(resolved_rows) / 60
                       if resolved_rows else None)
        return {
            "total": total, "open": open_, "critical": critical_open, "critical_total": critical_total,
            "resolved": resolved, "closed": by_status[IncidentStatus.CLOSED.value],
            "sla_violations": self.repos.violations.count(),
            "sla_breached_incidents": self._count(Incident.sla_status == SlaStatus.BREACHED),
            "sla_at_risk": self._count(Incident.sla_status == SlaStatus.AT_RISK, Incident.status.in_(OPEN_STATUSES)),
            "unassigned": self._count(Incident.assigned_technician_id.is_(None), Incident.status.in_(OPEN_STATUSES)),
            "sla_compliance_percent": compliance,
            "avg_resolution_minutes": round(avg_minutes, 1) if avg_minutes is not None else None,
            "avg_feedback_rating": (round(float(r), 2) if (r := self.repos.feedback.average_rating()) else None),
            "by_priority": by_priority, "by_status": by_status,
        }

    def _grouped(self, model_cls, fk) -> list:
        rows = self.session.execute(
            select(model_cls.id, model_cls.name, func.count(Incident.id))
            .select_from(model_cls).join(Incident, fk == model_cls.id, isouter=True)
            .group_by(model_cls.id, model_cls.name).order_by(model_cls.name)).all()
        result = []
        for mid, name, total in rows:
            open_ = self._count(fk == mid, Incident.status.in_(OPEN_STATUSES))
            breached = self._count(fk == mid, Incident.sla_status == SlaStatus.BREACHED)
            p1 = self._count(fk == mid, Incident.priority == Priority.P1)
            result.append({"id": mid, "name": name, "total": total, "open": open_,
                           "critical": p1, "sla_breached": breached})
        return result

    def by_service(self) -> list:
        return self._grouped(Service, Incident.service_id)

    def by_category(self) -> list:
        return self._grouped(IncidentCategory, Incident.category_id)

    def trends(self, days: int = 14) -> list:
        today = self.clock.now().date()
        start = today - timedelta(days=days - 1)
        created, resolved = defaultdict(int), defaultdict(int)
        since = self.clock.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
        for (c_at,) in self.session.execute(select(Incident.created_at).where(Incident.created_at >= since)).all():
            created[c_at.date()] += 1
        for (r_at,) in self.session.execute(
                select(Incident.resolved_at).where(Incident.resolved_at.is_not(None), Incident.resolved_at >= since)).all():
            resolved[r_at.date()] += 1
        out = []
        for i in range(days):
            d = start + timedelta(days=i)
            out.append({"date": d.isoformat(), "created": created[d], "resolved": resolved[d]})
        return out

    def category_service_matrix(self) -> list:
        rows = self.session.execute(
            select(IncidentCategory.name, Service.name, func.count(Incident.id))
            .join(Incident, Incident.category_id == IncidentCategory.id)
            .join(Service, Service.id == Incident.service_id)
            .group_by(IncidentCategory.name, Service.name)).all()
        return [{"category": c, "service": s, "count": n} for c, s, n in rows]

    # ------------------------------------------------------------------ dashboards
    def dashboard(self, actor) -> dict:
        if actor.role == Role.ADMIN:
            return self._admin(actor)
        if actor.role == Role.TECHNICIAN:
            return self._technician(actor)
        return self._employee(actor)

    def _notif_block(self, actor) -> dict:
        items = self.repos.notifications.for_user(actor.id, limit=5)
        return {"unread": self.repos.notifications.unread_count(actor.id),
                "recent": [{"id": n.id, "subject": n.subject, "body": n.body, "is_read": n.is_read,
                            "created_at": n.created_at,
                            "incident_number": n.incident.number if n.incident else None} for n in items]}

    def _employee(self, actor) -> dict:
        mine = Incident.reporter_id == actor.id
        recent = self.session.scalars(
            select(Incident).where(mine).order_by(Incident.updated_at.desc()).limit(6)).all()
        waiting_verify = self.session.scalars(
            select(Incident).where(mine, Incident.status == IncidentStatus.RESOLVED)
            .order_by(Incident.resolved_at.desc())).all()
        info_requests = self.session.scalars(
            select(Incident).where(mine, Incident.awaiting_info.is_(True), Incident.status.in_(OPEN_STATUSES))).all()
        return {
            "role": "EMPLOYEE",
            "counts": {
                "total": self._count(mine),
                "open": self._count(mine, Incident.status.in_(OPEN_STATUSES)),
                "resolved": self._count(mine, Incident.status.in_(DONE_STATUSES)),
                "critical": self._count(mine, Incident.priority == Priority.P1, Incident.status.in_(OPEN_STATUSES)),
            },
            "recent_incidents": self.presenter.list_items(list(recent)),
            "pending_verification": self.presenter.list_items(list(waiting_verify)),
            "pending_info_requests": self.presenter.list_items(list(info_requests)),
            "notifications": self._notif_block(actor),
        }

    def _technician(self, actor) -> dict:
        mine = Incident.assigned_technician_id == actor.id
        queue = self.session.scalars(
            select(Incident).where(mine, Incident.status.in_(OPEN_STATUSES))
            .order_by(Incident.priority_score.desc(), Incident.resolution_deadline)).all()
        profile = actor.technician_profile
        active = self.repos.technicians.workload_for(actor.id)
        by_priority = {p.value: 0 for p in Priority}
        for inc in queue:
            by_priority[inc.priority.value] += 1
        items = self.presenter.list_items(list(queue))
        return {
            "role": "TECHNICIAN",
            "workload": {"active": active, "limit": profile.workload_limit if profile else 0,
                         "is_available": profile.is_available if profile else False,
                         "utilization_percent": round(active / profile.workload_limit * 100)
                         if profile and profile.workload_limit else 0},
            "counts": {
                "assigned_open": len(queue),
                "pending_acknowledgement": sum(1 for i in queue if i.status == IncidentStatus.ASSIGNED),
                "in_progress": sum(1 for i in queue if i.status == IncidentStatus.IN_PROGRESS),
                "resolved_by_me": self._count(mine, Incident.status.in_(DONE_STATUSES)),
                "sla_breached": sum(1 for i in queue if i.sla_status == SlaStatus.BREACHED),
                "sla_at_risk": sum(1 for i in queue if i.sla_status == SlaStatus.AT_RISK),
            },
            "by_priority": by_priority,
            "queue": items,
            "sla_countdown": [self._countdown(i) for i in queue[:8]],
            "notifications": self._notif_block(actor),
        }

    def _countdown(self, inc: Incident) -> dict:
        info = self.sla.describe(inc)
        phase = info["response"] if info["response"]["pending"] else info["resolution"]
        return {"number": inc.number, "title": inc.title, "priority": inc.priority.value,
                "phase": phase["type"], "deadline": phase["deadline"],
                "remaining_seconds": phase["remaining_seconds"], "state": phase["state"]}

    def _admin(self, actor) -> dict:
        overview = self.overview()
        at_risk = [{**self.presenter.list_item(inc), "sla": info} for inc, info in self.sla.at_risk(8)]
        recent_audit = self.repos.audit.search(page=1, page_size=6)[0]
        return {
            "role": "ADMIN",
            "overview": overview,
            "trends": self.trends(14),
            "technician_workload": self.users.workload(actor),
            "by_service": self.by_service(),
            "by_category": self.by_category(),
            "at_risk": at_risk,
            "recent_activity": [self.presenter.timeline_entry(e) | {
                "incident_number": e.incident.number if e.incident else None} for e in recent_audit],
            "notifications": self._notif_block(actor),
        }
