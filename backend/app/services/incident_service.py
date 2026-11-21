"""Incident workflows: create, classify, prioritise, assign, transition, annotate."""
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from app.domain.enums import (
    DONE_STATUSES, OPEN_STATUSES, ActorKind, EventType, IncidentStatus, NoteType, Role,
)
from app.domain.exceptions import (
    ConflictError, IncidentNotFoundError, InvalidInputError, NotFoundError, PermissionDeniedError,
    ServiceNotFoundError,
)
from app.domain.lifecycle import LifecycleManager
from app.models import EmployeeFeedback, Incident, InvestigationNote, Resolution, User
from app.repositories import IncidentFilters
from app.services.base import BaseService, transactional
from app.services.incident_factory import IncidentFactory
from app.strategies.priority import AffectedUsersPolicy, PriorityResult

ALL_STATUS_ALIASES = {
    "OPEN": [s.value for s in OPEN_STATUSES],
    "DONE": [s.value for s in DONE_STATUSES],
    "ACTIVE": [s.value for s in (IncidentStatus.ASSIGNED, IncidentStatus.ACKNOWLEDGED, IncidentStatus.IN_PROGRESS)],
}

TECH_NOTE_TYPES = {NoteType.INVESTIGATION, NoteType.INFO_REQUEST, NoteType.COMMENT}
REPORTER_NOTE_TYPES = {NoteType.ADDITIONAL_INFO, NoteType.INFO_REPLY}


@dataclass
class CreateResult:
    incident: Incident
    duplicates: list = field(default_factory=list)
    assigned: bool = False
    assignment_message: str = ""


def parse_status_filter(value: Optional[str]) -> list:
    if not value:
        return []
    out = []
    for part in value.split(","):
        part = part.strip().upper()
        if not part:
            continue
        if part in ALL_STATUS_ALIASES:
            out.extend(ALL_STATUS_ALIASES[part])
        else:
            try:
                out.append(IncidentStatus(part).value)
            except ValueError:
                raise InvalidInputError(f"Unknown status '{part}'.") from None
    return out


class IncidentService(BaseService):
    def __init__(self, session, repos, bus, clock, settings_service, sla_service,
                 assignment_service, intelligence_service):
        super().__init__(session, repos, bus, clock)
        self.settings_service = settings_service
        self.sla = sla_service
        self.assignment = assignment_service
        self.intelligence = intelligence_service

    # ------------------------------------------------------------------ access control
    @staticmethod
    def actor_kinds(user: Optional[User], incident: Incident) -> set:
        if user is None:
            return {ActorKind.SYSTEM}
        kinds = set()
        if user.role == Role.ADMIN:
            kinds.add(ActorKind.ADMIN)
        if incident.assigned_technician_id == user.id:
            kinds.add(ActorKind.ASSIGNED_TECH)
        if incident.reporter_id == user.id:
            kinds.add(ActorKind.REPORTER)
        return kinds

    def can_view(self, user: User, incident: Incident) -> bool:
        if user.role == Role.ADMIN:
            return True
        if user.role == Role.EMPLOYEE:
            return incident.reporter_id == user.id
        if user.role == Role.TECHNICIAN:
            return incident.assigned_technician_id == user.id
        return False

    def get_for_actor(self, actor: User, number: str) -> Incident:
        incident = self.repos.incidents.get_by_number(number)
        if incident is None:
            raise IncidentNotFoundError(f"Incident {number} was not found.")
        if not self.can_view(actor, incident):
            raise PermissionDeniedError("You do not have access to this incident.")
        return incident

    # ------------------------------------------------------------------ list / search
    def list_incidents(self, actor: User, filters: IncidentFilters) -> tuple:
        if actor.role == Role.EMPLOYEE:
            filters.reporter_id = actor.id
        elif actor.role == Role.TECHNICIAN:
            filters.scope_technician_id = actor.id
        return self.repos.incidents.search(filters)

    # ------------------------------------------------------------------ create
    @transactional
    def create_incident(self, actor: User, data: dict) -> CreateResult:
        if actor.role == Role.TECHNICIAN:
            raise PermissionDeniedError("Technicians cannot report incidents. Use an employee account.")
        now = self.clock.now()

        service = self.repos.services.get(data["service_id"])
        if service is None or not service.is_active:
            raise ServiceNotFoundError("The selected service does not exist or is inactive.")

        criticality, overridden = service.business_criticality, False
        requested = data.get("business_criticality")
        if requested is not None and actor.role == Role.ADMIN and requested != service.business_criticality:
            criticality, overridden = requested, True

        category, source = self._resolve_category(data)
        effective_impact, priority_result = self._score(
            data["impact"], data.get("affected_users"), data["urgency"], criticality)
        policy = self.sla.select_policy(service.id, priority_result.priority)

        incident = IncidentFactory.create(
            title=data["title"], description=data["description"], reporter=actor, service=service,
            category=category, category_source=source, impact=data["impact"], urgency=data["urgency"],
            criticality=criticality, criticality_overridden=overridden, priority_result=priority_result,
            affected_system=data.get("affected_system"), affected_users=data.get("affected_users"), now=now,
            effective_impact=effective_impact,
        )
        self.repos.incidents.add(incident)
        IncidentFactory.assign_number(incident)
        self.sla.apply_policy(incident, policy)
        self.session.flush()

        self.emit(EventType.INCIDENT_CREATED,
                  f"{incident.number} created by {actor.full_name} for {service.name}",
                  incident=incident, actor=actor, new_state=IncidentStatus.NEW.value)

        # NEW -> CLASSIFIED, performed by the system
        LifecycleManager.validate(incident.status, IncidentStatus.CLASSIFIED, {ActorKind.SYSTEM})
        incident.status = IncidentStatus.CLASSIFIED
        cat_name = category.name if category else "Uncategorised"
        self.emit(EventType.INCIDENT_CLASSIFIED,
                  f"Incident classified as {cat_name} ({self._source_label(source)})",
                  incident=incident, previous_state=IncidentStatus.NEW.value,
                  new_state=IncidentStatus.CLASSIFIED.value, category=cat_name, source=source)
        self.emit(EventType.PRIORITY_CALCULATED,
                  f"Priority calculated as {priority_result.priority.value}: {priority_result.explanation}. "
                  f"SLA '{policy.name}': respond within {policy.response_minutes} min, "
                  f"resolve within {policy.resolution_minutes} min",
                  incident=incident, score=priority_result.score, priority=priority_result.priority.value,
                  policy_id=policy.id)

        duplicates = self.intelligence.find_duplicates(
            incident.title, incident.description, incident.service_id, incident.category_id,
            exclude_id=incident.id)
        if duplicates:
            self.emit(EventType.DUPLICATE_DETECTED,
                      "Possible duplicate of " + ", ".join(d["incident"].number for d in duplicates[:3]),
                      incident=incident,
                      candidates=[{"number": d["incident"].number, "similarity": d["similarity"]} for d in duplicates])

        result = CreateResult(incident=incident, duplicates=duplicates)
        if self.settings_service.auto_assign():
            self._auto_assign(incident, result)
        else:
            result.assignment_message = "Automatic assignment is switched off. An administrator will assign it."
        self.sla.refresh_status(incident, now)
        return result

    def _resolve_category(self, data: dict) -> tuple:
        if data.get("category_id"):
            category = self.repos.categories.get(data["category_id"])
            if category is None or not category.is_active:
                raise InvalidInputError("The selected category does not exist or is inactive.")
            return category, "USER"
        suggestion = self.intelligence.suggest_category(data["title"], data["description"])["suggestion"]
        if suggestion:
            return self.repos.categories.get(suggestion["category_id"]), "AUTO"
        fallback = self.repos.categories.get_by_name("Application") or next(iter(self.repos.categories.list(True)), None)
        return fallback, "DEFAULT"

    @staticmethod
    def _source_label(source: str) -> str:
        return {"USER": "chosen by the reporter", "AUTO": "suggested from keywords",
                "DEFAULT": "default category, no keyword matched", "MANUAL": "set manually"}.get(source, source)

    def _auto_assign(self, incident: Incident, result: CreateResult) -> None:
        rec = self.assignment.recommend(incident)
        if not rec["eligible"]:
            reasons = "; ".join(f"{i['name']}: {', '.join(i['reasons'])}" for i in rec["ineligible"]) or "No technicians exist."
            msg = f"No eligible technician was found, so the incident stays unassigned. {reasons}"
            self.emit(EventType.NO_TECHNICIAN_AVAILABLE, msg, incident=incident, ineligible=rec["ineligible"])
            result.assignment_message = "No eligible technician is available right now. Administrators were notified."
            return
        top = rec["eligible"][0]
        tech = self.repos.users.get(top.technician_id)
        self._perform_assignment(incident, tech, actor=None, strategy=rec["strategy"]["label"],
                                 reasons=top.reasons, score=top.score)
        result.assigned = True
        result.assignment_message = f"Assigned to {tech.full_name}."

    # ------------------------------------------------------------------ assignment
    def _perform_assignment(self, incident: Incident, tech: User, actor: Optional[User], *,
                            strategy: Optional[str] = None, reasons: Optional[list] = None,
                            score: Optional[float] = None, overridden: Optional[list] = None) -> None:
        kinds = self.actor_kinds(actor, incident)
        rule = LifecycleManager.validate(incident.status, IncidentStatus.ASSIGNED, kinds)
        previous_tech = incident.assigned_technician_id
        previous_status = incident.status
        incident.assigned_technician = tech
        incident.assigned_technician_id = tech.id
        incident.status = IncidentStatus.ASSIGNED
        incident.updated_at = self.clock.now()
        how = f"by {actor.full_name}" if actor else f"automatically ({strategy})"
        text = f"Assigned to {tech.full_name} {how}"
        if previous_tech:
            text = f"Reassigned from {self._name(previous_tech)} to {tech.full_name} {how}"
        if overridden:
            text += ". Admin override of: " + "; ".join(overridden)
        self.emit(rule.event, text, incident=incident, actor=actor, previous_state=previous_status.value,
                  new_state=IncidentStatus.ASSIGNED.value, technician_id=tech.id,
                  previous_technician_id=previous_tech, strategy=strategy, reasons=reasons, score=score,
                  overridden=overridden or [])
        self.sla.refresh_status(incident)

    def _name(self, user_id: int) -> str:
        user = self.repos.users.get(user_id)
        return user.full_name if user else f"user {user_id}"

    @transactional
    def assign(self, actor: User, number: str, technician_id: int, override: bool = False) -> Incident:
        incident = self.get_for_actor(actor, number)
        if actor.role != Role.ADMIN:
            raise PermissionDeniedError("Only administrators can assign or reassign incidents.")
        tech = self.repos.users.get(technician_id)
        if tech is None or tech.role != Role.TECHNICIAN:
            raise NotFoundError("Technician not found.")
        if incident.assigned_technician_id == tech.id and incident.status in OPEN_STATUSES:
            raise ConflictError(f"{number} is already assigned to {tech.full_name}.")
        # lifecycle check first so that closed/resolved incidents give a clear 409
        LifecycleManager.validate(incident.status, IncidentStatus.ASSIGNED, self.actor_kinds(actor, incident))
        overridden = self.assignment.ensure_assignable(incident, tech, override=override)
        self._perform_assignment(incident, tech, actor, overridden=overridden)
        return incident

    # ------------------------------------------------------------------ transitions
    @transactional
    def transition(self, actor: User, number: str, to_status: str, *, reason: Optional[str] = None,
                   resolution_summary: Optional[str] = None, root_cause: Optional[str] = None,
                   closure_note: Optional[str] = None, technician_id: Optional[int] = None,
                   override: bool = False) -> Incident:
        incident = self.get_for_actor(actor, number)
        target = IncidentStatus(to_status)
        if target == IncidentStatus.ASSIGNED:
            if technician_id is None:
                raise InvalidInputError("technician_id is required to assign or reassign an incident.")
            return self.assign(actor, number, technician_id, override)

        kinds = self.actor_kinds(actor, incident)
        payload = {"reason": reason, "resolution_summary": resolution_summary, "root_cause": root_cause}
        rule = LifecycleManager.validate(incident.status, target, kinds, payload)
        now = self.clock.now()
        previous = incident.status
        incident.status = target
        incident.updated_at = now
        meta: dict = {}
        by = actor.full_name

        if target == IncidentStatus.ACKNOWLEDGED:
            if incident.acknowledged_at is None:
                incident.acknowledged_at = now
            text = f"{by} acknowledged the incident"
        elif target == IncidentStatus.IN_PROGRESS and previous == IncidentStatus.ACKNOWLEDGED:
            text = f"{by} started the investigation"
        elif target == IncidentStatus.IN_PROGRESS:  # reopened from RESOLVED
            incident.resolved_at = None
            incident.verified_at = None
            incident.reopen_count += 1
            self.repos.notes.add(InvestigationNote(
                incident_id=incident.id, author_id=actor.id, note_type=NoteType.REOPEN,
                body=reason.strip(), is_internal=False, created_at=now))
            text = f"{by} reopened the incident: {reason.strip()}"
            meta["reason"] = reason.strip()
        elif target == IncidentStatus.RESOLVED:
            self._save_resolution(incident, actor, resolution_summary.strip(), root_cause.strip(), now)
            incident.resolved_at = now
            incident.awaiting_info = False
            text = f"{by} resolved the incident. Root cause: {root_cause.strip()}"
            meta.update(summary=resolution_summary.strip(), root_cause=root_cause.strip())
        elif target == IncidentStatus.VERIFIED:
            incident.verified_at = now
            text = f"{by} verified the resolution"
        elif target == IncidentStatus.CLOSED:
            incident.closed_at = now
            incident.closure_note = (closure_note or "").strip() or None
            text = f"{by} closed the incident" + (f": {incident.closure_note}" if incident.closure_note else "")
        else:  # pragma: no cover - guarded by lifecycle rules
            text = f"Status changed to {target.value}"

        self.emit(rule.event, text, incident=incident, actor=actor, previous_state=previous.value,
                  new_state=target.value, **meta)

        if target == IncidentStatus.ACKNOWLEDGED:
            self.sla.on_acknowledged(incident, now)
        elif target == IncidentStatus.RESOLVED:
            self.sla.on_resolved(incident, now)
        else:
            self.sla.refresh_status(incident, now)
        return incident

    def _save_resolution(self, incident, actor, summary, root_cause, now) -> None:
        existing = self.repos.resolutions.get_for_incident(incident.id)
        if existing:
            existing.summary, existing.root_cause = summary, root_cause
            existing.technician_id, existing.created_at = actor.id, now
            incident.resolution = existing
        else:
            resolution = Resolution(incident=incident, technician_id=actor.id, summary=summary,
                                    root_cause=root_cause, created_at=now)
            self.repos.resolutions.add(resolution)

    # ------------------------------------------------------------------ notes
    @transactional
    def add_note(self, actor: User, number: str, note_type: str, body: str,
                 is_internal: Optional[bool] = None) -> InvestigationNote:
        incident = self.get_for_actor(actor, number)
        ntype = NoteType(note_type)
        kinds = self.actor_kinds(actor, incident)
        body = body.strip()
        if not body:
            raise InvalidInputError("The note cannot be empty.")
        if incident.status == IncidentStatus.CLOSED:
            raise ConflictError("Closed incidents are read-only.")
        is_admin = ActorKind.ADMIN in kinds
        allowed = set()
        if ActorKind.ASSIGNED_TECH in kinds or is_admin:
            allowed |= TECH_NOTE_TYPES
        if ActorKind.REPORTER in kinds or is_admin:
            allowed |= REPORTER_NOTE_TYPES
        if ntype not in allowed:
            raise PermissionDeniedError("You cannot add this type of note to this incident.")
        if ntype == NoteType.INFO_REQUEST and incident.assigned_technician_id is None:
            raise ConflictError("An information request needs an assigned technician.")

        internal = (ntype == NoteType.INVESTIGATION) if is_internal is None else bool(is_internal)
        if ntype != NoteType.INVESTIGATION and ntype != NoteType.COMMENT:
            internal = False
        if actor.role == Role.EMPLOYEE:
            internal = False
        now = self.clock.now()
        note = self.repos.notes.add(InvestigationNote(
            incident_id=incident.id, author_id=actor.id, note_type=ntype, body=body,
            is_internal=internal, created_at=now))
        incident.updated_at = now
        if ntype == NoteType.INFO_REQUEST:
            incident.awaiting_info = True
            self.emit(EventType.INFO_REQUESTED, f"{actor.full_name} requested more information",
                      incident=incident, actor=actor, body=body)
        elif ntype in REPORTER_NOTE_TYPES:
            if ntype == NoteType.INFO_REPLY:
                incident.awaiting_info = False
            self.emit(EventType.INFO_PROVIDED,
                      f"{actor.full_name} " + ("answered the information request" if ntype == NoteType.INFO_REPLY
                                                else "added more information"),
                      incident=incident, actor=actor, body=body)
        else:
            kind = "an internal investigation note" if internal else "a comment"
            self.emit(EventType.NOTE_ADDED, f"{actor.full_name} added {kind}", incident=incident, actor=actor,
                      note_type=ntype.value, internal=internal)
        return note

    def list_notes(self, actor: User, number: str) -> list:
        incident = self.get_for_actor(actor, number)
        include_internal = actor.role in (Role.ADMIN, Role.TECHNICIAN)
        return self.repos.notes.for_incident(incident.id, include_internal)

    # ------------------------------------------------------------------ feedback
    @transactional
    def submit_feedback(self, actor: User, number: str, rating: int, comment: Optional[str]) -> EmployeeFeedback:
        incident = self.get_for_actor(actor, number)
        if incident.reporter_id != actor.id:
            raise PermissionDeniedError("Only the person who reported the incident can give feedback.")
        if incident.status not in DONE_STATUSES:
            raise ConflictError("Feedback can be given after the incident has been resolved.")
        if self.repos.feedback.get_for_incident(incident.id):
            raise ConflictError("Feedback has already been submitted for this incident.")
        fb = self.repos.feedback.add(EmployeeFeedback(
            incident_id=incident.id, employee_id=actor.id, rating=rating,
            comment=(comment or "").strip() or None, created_at=self.clock.now()))
        incident.feedback = fb
        self.emit(EventType.FEEDBACK_SUBMITTED, f"{actor.full_name} rated the resolution {rating}/5",
                  incident=incident, actor=actor, rating=rating)
        return fb

    # ------------------------------------------------------------------ update
    PRIORITY_FIELDS = ("impact", "urgency", "business_criticality", "service_id")
    TEXT_FIELDS = ("title", "description", "affected_system", "affected_users")

    @transactional
    def update_incident(self, actor: User, number: str, changes: dict) -> Incident:
        incident = self.get_for_actor(actor, number)
        if incident.status == IncidentStatus.CLOSED:
            raise ConflictError("Closed incidents are read-only.")
        kinds = self.actor_kinds(actor, incident)
        is_admin = ActorKind.ADMIN in kinds
        changes = {k: v for k, v in changes.items() if k in
                   self.PRIORITY_FIELDS + self.TEXT_FIELDS + ("category_id", "duplicate_of_number")}
        if not changes:
            raise InvalidInputError("No changes were supplied.")

        priority_touched = [k for k in self.PRIORITY_FIELDS if k in changes]
        if (priority_touched or "duplicate_of_number" in changes) and not is_admin:
            raise PermissionDeniedError("Only administrators can change priority-driving fields.")
        if any(k in changes for k in self.TEXT_FIELDS) and not (is_admin or ActorKind.REPORTER in kinds):
            raise PermissionDeniedError("Only the reporter or an administrator can edit the incident text.")
        if "category_id" in changes and not (is_admin or ActorKind.ASSIGNED_TECH in kinds):
            raise PermissionDeniedError("Only the assigned technician or an administrator can change the category.")
        if any(k in changes for k in self.TEXT_FIELDS) and incident.status in DONE_STATUSES and not is_admin:
            raise ConflictError("A resolved incident can no longer be edited by the reporter.")

        now = self.clock.now()
        diffs = []
        for fld in self.TEXT_FIELDS:
            if fld in changes and changes[fld] != getattr(incident, fld):
                new = changes[fld].strip() if isinstance(changes[fld], str) else changes[fld]
                diffs.append(fld)
                setattr(incident, fld, new or None if fld == "affected_system" else new)

        if "category_id" in changes:
            category = self.repos.categories.get(changes["category_id"])
            if category is None or not category.is_active:
                raise InvalidInputError("The selected category does not exist or is inactive.")
            if category.id != incident.category_id:
                old = incident.category.name if incident.category else "none"
                incident.category, incident.category_id, incident.category_source = category, category.id, "MANUAL"
                self.emit(EventType.CATEGORY_CHANGED, f"Category changed from {old} to {category.name} by {actor.full_name}",
                          incident=incident, actor=actor, from_category=old, to_category=category.name)

        if "duplicate_of_number" in changes:
            self._link_duplicate(incident, actor, changes["duplicate_of_number"])

        if priority_touched:
            self._recalculate_priority(incident, actor, changes, now)
        elif "affected_users" in diffs:
            new_effective, _ = self._effective_impact(incident.impact, incident.affected_users)
            if new_effective != (incident.effective_impact or incident.impact):
                self._recalculate_priority(incident, actor, {}, now,
                                           reason=f"the number of affected users changed to {incident.affected_users}")

        if diffs:
            self.emit(EventType.INCIDENT_UPDATED, f"{actor.full_name} updated: {', '.join(diffs)}",
                      incident=incident, actor=actor, fields=diffs)
        incident.updated_at = now
        self.sla.refresh_status(incident, now)
        return incident

    def _link_duplicate(self, incident, actor, number) -> None:
        if not number:
            incident.duplicate_of, incident.duplicate_of_id = None, None
            self.emit(EventType.DUPLICATE_LINKED, "Duplicate link removed", incident=incident, actor=actor)
            return
        other = self.repos.incidents.get_by_number(number)
        if other is None or other.id == incident.id:
            raise InvalidInputError("Choose another existing incident number to link.")
        incident.duplicate_of, incident.duplicate_of_id = other, other.id
        self.emit(EventType.DUPLICATE_LINKED, f"Marked as related to {other.number} (nothing is merged)",
                  incident=incident, actor=actor, other=other.number)

    # ------------------------------------------------------------------ priority helpers
    def _effective_impact(self, impact: int, affected_users) -> tuple:
        """Impact used for scoring: the reported impact, raised by the affected-users policy."""
        if not self.settings_service.affected_users_adjustment():
            return impact, None
        return AffectedUsersPolicy.adjust(impact, affected_users)

    def _score(self, impact: int, affected_users, urgency: int, criticality: int) -> tuple:
        """Return (effective_impact, PriorityResult) using the strategy chosen in Settings."""
        effective, note = self._effective_impact(impact, affected_users)
        result = self.settings_service.priority_strategy().calculate(effective, urgency, criticality)
        if note:
            result = PriorityResult(result.score, result.priority, f"{note} {result.explanation}")
        return effective, result

    def preview_priority(self, actor: User, data: dict) -> dict:
        """What-if calculation for the report form. Reads only, stores nothing."""
        service = self.repos.services.get(data["service_id"])
        if service is None or not service.is_active:
            raise ServiceNotFoundError("The selected service does not exist or is inactive.")
        criticality = service.business_criticality
        if data.get("business_criticality") is not None and actor.role == Role.ADMIN:
            criticality = data["business_criticality"]
        effective, result = self._score(data["impact"], data.get("affected_users"), data["urgency"], criticality)
        return {"score": result.score, "priority": result.priority.value, "effective_impact": effective,
                "business_criticality": criticality, "explanation": result.explanation,
                "impact_raised": effective != data["impact"]}

    def _recalculate_priority(self, incident, actor, changes, now, reason=None) -> None:
        old_priority, old_score = incident.priority, incident.priority_score
        old_deadlines = (incident.response_deadline, incident.resolution_deadline)
        if "service_id" in changes and changes["service_id"] != incident.service_id:
            service = self.repos.services.get(changes["service_id"])
            if service is None or not service.is_active:
                raise ServiceNotFoundError("The selected service does not exist or is inactive.")
            incident.service, incident.service_id = service, service.id
            if not incident.criticality_overridden:
                incident.business_criticality = service.business_criticality
        for fld in ("impact", "urgency"):
            if fld in changes:
                setattr(incident, fld, changes[fld])
        if "business_criticality" in changes:
            incident.business_criticality = changes["business_criticality"]
            incident.criticality_overridden = changes["business_criticality"] != incident.service.business_criticality
        effective, result = self._score(
            incident.impact, incident.affected_users, incident.urgency, incident.business_criticality)
        incident.effective_impact = effective
        incident.priority, incident.priority_score = result.priority, result.score
        policy = self.sla.select_policy(incident.service_id, result.priority)
        self.sla.apply_policy(incident, policy)
        if (incident.response_deadline, incident.resolution_deadline) > old_deadlines:
            incident.response_warned_at = incident.resolution_warned_at = None
        self.emit(EventType.PRIORITY_CHANGED,
                  f"Priority recalculated{f' because {reason}' if reason else f' by {actor.full_name}'}: {old_priority.value} (score {old_score}) -> "
                  f"{result.priority.value} (score {result.score}). {result.explanation}. "
                  f"New SLA: respond in {policy.response_minutes} min, resolve in {policy.resolution_minutes} min.",
                  incident=incident, actor=actor, previous_state=old_priority.value,
                  new_state=result.priority.value, old_score=old_score, new_score=result.score)

    # ------------------------------------------------------------------ introspection
    def allowed_transitions(self, actor: User, incident: Incident) -> list:
        kinds = self.actor_kinds(actor, incident)
        targets = LifecycleManager.allowed_next(incident.status, kinds)
        return [t for t in targets if t != IncidentStatus.ASSIGNED.value]

    def timeline(self, actor: User, number: str) -> list:
        incident = self.get_for_actor(actor, number)
        entries = self.repos.audit.for_incident(incident.id)
        if actor.role == Role.EMPLOYEE:
            hidden = {EventType.DUPLICATE_DETECTED.value, EventType.NO_TECHNICIAN_AVAILABLE.value,
                      EventType.INCIDENT_ESCALATED.value, EventType.SLA_WARNING.value}
            entries = [e for e in entries if e.action not in hidden]
        return entries
