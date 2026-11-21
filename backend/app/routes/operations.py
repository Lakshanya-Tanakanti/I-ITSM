"""Notifications, audit log, reports, SLA monitoring and dashboards."""
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.domain.exceptions import InvalidInputError
from app.middleware.dependencies import get_container, get_current_user, require_admin
from app.models import User
from app.schemas.common import Message, paginate
from app.services.container import Container

router = APIRouter(tags=["Notifications, audit and reports"])


def _notification(n) -> dict:
    return {"id": n.id, "incident_number": n.incident.number if n.incident else None,
            "incident_title": n.incident.title if n.incident else None, "channel": n.channel.value,
            "subject": n.subject, "body": n.body, "event_type": n.event_type, "is_read": n.is_read,
            "delivery_status": n.delivery_status, "created_at": n.created_at}


# --------------------------------------------------------------------------- notifications
@router.get("/notifications")
def list_notifications(unread_only: bool = False, limit: int = Query(default=50, ge=1, le=200),
                       user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    data = c.notifications.list_for(user, unread_only, limit)
    return {"items": [_notification(n) for n in data["items"]], "unread_count": data["unread_count"],
            "total": data["total"]}


@router.post("/notifications/read-all", response_model=Message)
def read_all(user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    n = c.notifications.mark_all_read(user)
    return {"message": f"{n} notification(s) marked as read."}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return _notification(c.notifications.mark_read(user, notification_id))


@router.get("/admin/email-outbox")
def email_outbox(limit: int = Query(default=100, ge=1, le=500), admin: User = Depends(require_admin),
                 c: Container = Depends(get_container)):
    return [{**_notification(n), "to_name": n.recipient.full_name, "to_email": n.recipient.email}
            for n in c.notifications.outbox(limit)]


# --------------------------------------------------------------------------- audit
def _day_start(d: Optional[date]) -> Optional[datetime]:
    return datetime.combine(d, time.min, tzinfo=timezone.utc) if d else None


@router.get("/audit-logs")
def audit_logs(number: Optional[str] = None, actor_id: Optional[int] = None, action: Optional[str] = None,
               from_date: Optional[date] = None, to_date: Optional[date] = None,
               q: Optional[str] = Query(default=None, max_length=200),
               page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=200),
               admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    incident_id = None
    if number:
        inc = c.repos.incidents.get_by_number(number)
        if inc is None:
            return paginate([], 0, page, page_size)
        incident_id = inc.id
    if from_date and to_date and from_date > to_date:
        raise InvalidInputError("The start date must not be after the end date.")
    end = _day_start(to_date + timedelta(days=1)) if to_date else None
    rows, total = c.repos.audit.search(incident_id, actor_id, action, _day_start(from_date), end, q, page, page_size)
    items = []
    for e in rows:
        try:
            meta = json.loads(e.extra) if e.extra else None
        except ValueError:
            meta = None
        items.append({"id": e.id, "action": e.action, "description": e.description,
                      "actor_id": e.actor_id, "actor_name": e.actor.full_name if e.actor else "System",
                      "incident_number": e.incident.number if e.incident else None,
                      "previous_state": e.previous_state, "new_state": e.new_state,
                      "metadata": meta, "created_at": e.created_at})
    return paginate(items, total, page, page_size)


@router.get("/audit-logs/actions")
def audit_actions(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.repos.audit.distinct_actions()


# --------------------------------------------------------------------------- reports
@router.get("/reports/overview")
def report_overview(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.reports.overview()


@router.get("/reports/technician-workload")
def report_workload(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.users.workload(admin)


@router.get("/reports/by-service")
def report_by_service(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.reports.by_service()


@router.get("/reports/by-category")
def report_by_category(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.reports.by_category()


@router.get("/reports/trends")
def report_trends(days: int = Query(default=14, ge=2, le=90), admin: User = Depends(require_admin),
                  c: Container = Depends(get_container)):
    return c.reports.trends(days)


@router.get("/reports/category-service-matrix")
def report_matrix(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.reports.category_service_matrix()


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    """Role specific dashboard data (employee, technician or admin)."""
    return c.reports.dashboard(user)


# --------------------------------------------------------------------------- SLA
@router.get("/sla/at-risk")
def sla_at_risk(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return [{**c.presenter.list_item(inc), "sla": info} for inc, info in c.sla.at_risk(100)]


@router.get("/sla/violations")
def sla_violations(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return [{"id": v.id, "sla_type": v.sla_type.value, "deadline_at": v.deadline_at, "detected_at": v.detected_at,
             "incident_number": v.incident.number, "incident_title": v.incident.title,
             "priority": v.incident.priority.value, "service": v.incident.service.name,
             "technician": v.incident.assigned_technician.full_name if v.incident.assigned_technician else None,
             "late_minutes": round(max((v.detected_at - v.deadline_at).total_seconds(), 0) / 60, 1)}
            for v in c.sla.violations()]


@router.post("/sla/run-check")
def sla_run_check(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    """Runs the same check as the 60-second background monitor, on demand."""
    return c.sla.run_check()


@router.get("/sla/monitor")
def sla_monitor_status(request: Request, admin: User = Depends(require_admin)):
    monitor = getattr(request.app.state, "sla_monitor", None)
    if monitor is None:
        return {"running": False, "interval_seconds": None, "runs": 0, "last_run": None}
    return {"running": monitor.is_running, "interval_seconds": monitor.interval, "runs": monitor.runs,
            "last_run": monitor.last_run}
