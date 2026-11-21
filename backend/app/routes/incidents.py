from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domain.enums import Priority, Role, SlaStatus
from app.domain.exceptions import InvalidInputError, PermissionDeniedError
from app.middleware.dependencies import get_container, get_current_user
from app.models import User
from app.repositories import IncidentFilters
from app.schemas.common import paginate
from app.schemas.incident import (
    AssignRequest, CategorySuggestRequest, PriorityPreviewRequest, DuplicateCheckRequest, FeedbackCreate, IncidentCreate,
    IncidentUpdate, NoteCreate, TransitionRequest,
)
from app.services.container import Container
from app.services.incident_service import parse_status_filter

router = APIRouter(tags=["Incidents"])


def _csv(value: Optional[str], enum_cls=None) -> list:
    if not value:
        return []
    out = []
    for part in value.split(","):
        part = part.strip().upper()
        if not part:
            continue
        if enum_cls is not None:
            try:
                part = enum_cls(part).value
            except ValueError:
                raise InvalidInputError(f"Invalid value '{part}'.") from None
        out.append(part)
    return out


@router.post("/incidents", status_code=201)
def create_incident(body: IncidentCreate, user: User = Depends(get_current_user),
                    c: Container = Depends(get_container)):
    result = c.incidents.create_incident(user, body.model_dump())
    return {
        "incident": c.presenter.detail(result.incident, user),
        "duplicates": [c.presenter.duplicate_item(d) for d in result.duplicates],
        "assigned": result.assigned,
        "assignment_message": result.assignment_message,
    }


@router.get("/incidents")
def list_incidents(
    number: Optional[str] = Query(default=None, max_length=30),
    q: Optional[str] = Query(default=None, max_length=200),
    from_date: Optional[date] = None, to_date: Optional[date] = None,
    status: Optional[str] = Query(default=None, description="Comma list. Also OPEN, DONE, ACTIVE"),
    priority: Optional[str] = Query(default=None, description="Comma list of P1..P4"),
    category_id: Optional[int] = None, service_id: Optional[int] = None, technician_id: Optional[int] = None,
    sla_status: Optional[str] = Query(default=None, description="ON_TRACK, AT_RISK, BREACHED, MET"),
    unassigned: bool = False, awaiting_info: Optional[bool] = None,
    sort: str = "-created_at", page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user), c: Container = Depends(get_container),
):
    if from_date and to_date and from_date > to_date:
        raise InvalidInputError("The start date must not be after the end date.")
    filters = IncidentFilters(
        number=number, q=q, from_date=from_date, to_date=to_date,
        statuses=parse_status_filter(status), priorities=_csv(priority, Priority),
        category_id=category_id, service_id=service_id, technician_id=technician_id,
        sla_statuses=_csv(sla_status, SlaStatus), unassigned=unassigned, awaiting_info=awaiting_info,
        sort=sort, page=page, page_size=page_size,
    )
    items, total = c.incidents.list_incidents(user, filters)
    return paginate(c.presenter.list_items(items), total, page, page_size)


@router.get("/incidents/{number}")
def get_incident(number: str, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return c.presenter.detail(c.incidents.get_for_actor(user, number), user)


@router.patch("/incidents/{number}")
def update_incident(number: str, body: IncidentUpdate, user: User = Depends(get_current_user),
                    c: Container = Depends(get_container)):
    incident = c.incidents.update_incident(user, number, body.model_dump(exclude_unset=True))
    return c.presenter.detail(incident, user)


@router.post("/incidents/{number}/transition")
def transition(number: str, body: TransitionRequest, user: User = Depends(get_current_user),
               c: Container = Depends(get_container)):
    incident = c.incidents.transition(
        user, number, body.to_status.value, reason=body.reason, resolution_summary=body.resolution_summary,
        root_cause=body.root_cause, closure_note=body.closure_note, technician_id=body.technician_id,
        override=body.override)
    return c.presenter.detail(incident, user)


@router.post("/incidents/{number}/assign")
def assign(number: str, body: AssignRequest, user: User = Depends(get_current_user),
           c: Container = Depends(get_container)):
    incident = c.incidents.assign(user, number, body.technician_id, body.override)
    return c.presenter.detail(incident, user)


@router.get("/incidents/{number}/recommendations")
def recommendations(number: str, strategy: Optional[str] = None, user: User = Depends(get_current_user),
                    c: Container = Depends(get_container)):
    if user.role != Role.ADMIN:
        raise PermissionDeniedError("Only administrators can view technician recommendations.")
    incident = c.incidents.get_for_actor(user, number)
    rec = c.assignment.recommend(incident, strategy)
    return {
        "strategy": rec["strategy"],
        "eligible": [{"rank": r.rank, "technician_id": r.technician_id, "name": r.name, "score": r.score,
                      "reasons": r.reasons, "factors": r.factors, "team": r.team_name} for r in rec["eligible"]],
        "ineligible": rec["ineligible"],
        "available_strategies": c.settings.options()["assignment_strategies"],
    }


@router.get("/incidents/{number}/duplicates")
def duplicates(number: str, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    incident = c.incidents.get_for_actor(user, number)
    return [c.presenter.duplicate_item(d) for d in c.intelligence.duplicates_for(incident)]


@router.get("/incidents/{number}/related")
def related(number: str, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    if user.role == Role.EMPLOYEE:
        raise PermissionDeniedError("Correlation is available to technicians and administrators.")
    incident = c.incidents.get_for_actor(user, number)
    data = c.intelligence.related(incident)
    return {
        "summary": data["summary"], "service": data["service"],
        "related": [{"number": r["incident"].number, "title": r["incident"].title,
                     "status": r["incident"].status.value, "priority": r["incident"].priority.value,
                     "created_at": r["incident"].created_at, "reason": r["reason"]} for r in data["related"]],
    }


@router.get("/incidents/{number}/suggested-resolutions")
def suggested_resolutions(number: str, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    if user.role == Role.EMPLOYEE:
        raise PermissionDeniedError("Suggested resolutions are available to technicians and administrators.")
    incident = c.incidents.get_for_actor(user, number)
    return c.intelligence.suggested_resolutions(incident)


@router.get("/incidents/{number}/timeline")
def timeline(number: str, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return [c.presenter.timeline_entry(e) for e in c.incidents.timeline(user, number)]


@router.post("/incidents/{number}/notes", status_code=201)
def add_note(number: str, body: NoteCreate, user: User = Depends(get_current_user),
             c: Container = Depends(get_container)):
    note = c.incidents.add_note(user, number, body.note_type.value, body.body, body.is_internal)
    return c.presenter.note(note)


@router.get("/incidents/{number}/notes")
def list_notes(number: str, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return [c.presenter.note(n) for n in c.incidents.list_notes(user, number)]


@router.post("/incidents/{number}/feedback", status_code=201)
def feedback(number: str, body: FeedbackCreate, user: User = Depends(get_current_user),
             c: Container = Depends(get_container)):
    fb = c.incidents.submit_feedback(user, number, body.rating, body.comment)
    return {"rating": fb.rating, "comment": fb.comment, "created_at": fb.created_at}


# ---- helpers used by the report form (any signed in user) -----------------------------------
@router.post("/intelligence/suggest-category")
def suggest_category(body: CategorySuggestRequest, user: User = Depends(get_current_user),
                     c: Container = Depends(get_container)):
    return c.intelligence.suggest_category(body.title, body.description)


@router.post("/intelligence/preview-priority")
def preview_priority(body: PriorityPreviewRequest, user: User = Depends(get_current_user),
                     c: Container = Depends(get_container)):
    return c.incidents.preview_priority(user, body.model_dump())


@router.post("/intelligence/check-duplicates")
def check_duplicates(body: DuplicateCheckRequest, user: User = Depends(get_current_user),
                     c: Container = Depends(get_container)):
    if len(body.title.strip()) < 3:
        return []
    matches = c.intelligence.find_duplicates(body.title, body.description, body.service_id, body.category_id)
    return [c.presenter.duplicate_item(m) for m in matches]
