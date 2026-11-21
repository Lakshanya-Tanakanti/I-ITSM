"""Builds API-ready dictionaries from entities (role aware)."""
from typing import Optional

from app.domain.enums import DONE_STATUSES, ActorKind, IncidentStatus, Role
from app.models import Incident, User


def user_ref(user: Optional[User]) -> Optional[dict]:
    if user is None:
        return None
    return {"id": user.id, "full_name": user.full_name}


def user_full(user: User) -> dict:
    profile = user.technician_profile
    data = {
        "id": user.id, "employee_code": user.employee_code, "full_name": user.full_name,
        "email": user.email, "role": user.role.value, "department": user.department,
        "is_active": user.is_active, "created_at": user.created_at, "technician_profile": None,
    }
    if profile is not None:
        data["technician_profile"] = {
            "id": profile.id, "team_id": profile.team_id,
            "team_name": profile.team.name if profile.team else None,
            "experience_years": profile.experience_years, "is_available": profile.is_available,
            "workload_limit": profile.workload_limit,
            "skills": [{"category_id": s.category_id, "category_name": s.category.name,
                        "proficiency": s.proficiency} for s in profile.skills],
        }
    return data


class IncidentPresenter:
    def __init__(self, repos, sla_service, intelligence_service, incident_service):
        self.repos = repos
        self.sla = sla_service
        self.intelligence = intelligence_service
        self.incidents = incident_service

    # ------------------------------------------------------------------ list item
    def list_item(self, inc: Incident, workload: Optional[dict] = None, with_risk: bool = True) -> dict:
        risk = None
        if with_risk and inc.is_open:
            risk = self.intelligence.sla_risk(inc, workload)["level"]
        return {
            "id": inc.id, "number": inc.number, "title": inc.title, "status": inc.status.value,
            "priority": inc.priority.value, "priority_score": inc.priority_score,
            "category": {"id": inc.category.id, "name": inc.category.name} if inc.category else None,
            "service": {"id": inc.service.id, "name": inc.service.name},
            "reporter": user_ref(inc.reporter),
            "assigned_technician": user_ref(inc.assigned_technician),
            "created_at": inc.created_at, "updated_at": inc.updated_at,
            "response_deadline": inc.response_deadline, "resolution_deadline": inc.resolution_deadline,
            "acknowledged_at": inc.acknowledged_at, "resolved_at": inc.resolved_at,
            "sla_status": inc.sla_status.value, "risk_level": risk,
            "awaiting_info": inc.awaiting_info, "escalation_level": inc.escalation_level,
        }

    def list_items(self, incidents: list) -> list:
        workload = self.repos.technicians.workload_map()
        return [self.list_item(i, workload) for i in incidents]

    # ------------------------------------------------------------------ detail
    def detail(self, inc: Incident, actor: User) -> dict:
        kinds = self.incidents.actor_kinds(actor, inc)
        is_admin = ActorKind.ADMIN in kinds
        workload = self.repos.technicians.workload_map()
        resolution = inc.resolution
        feedback = inc.feedback
        base = self.list_item(inc, workload)
        base.update({
            "description": inc.description,
            "impact": inc.impact, "effective_impact": inc.effective_impact or inc.impact,
            "urgency": inc.urgency,
            "business_criticality": inc.business_criticality,
            "criticality_overridden": inc.criticality_overridden,
            "category_source": inc.category_source,
            "service": {"id": inc.service.id, "name": inc.service.name,
                        "business_criticality": inc.service.business_criticality},
            "reporter": {"id": inc.reporter.id, "full_name": inc.reporter.full_name,
                         "email": inc.reporter.email, "department": inc.reporter.department},
            "affected_system": inc.affected_system, "affected_users": inc.affected_users,
            "verified_at": inc.verified_at, "closed_at": inc.closed_at, "closure_note": inc.closure_note,
            "reopen_count": inc.reopen_count,
            "duplicate_of": ({"id": inc.duplicate_of.id, "number": inc.duplicate_of.number,
                              "title": inc.duplicate_of.title} if inc.duplicate_of else None),
            "sla": self.sla.describe(inc),
            "risk": self.intelligence.sla_risk(inc, workload),
            "resolution": ({"summary": resolution.summary, "root_cause": resolution.root_cause,
                            "technician": user_ref(resolution.technician), "created_at": resolution.created_at}
                           if resolution else None),
            "feedback": ({"rating": feedback.rating, "comment": feedback.comment,
                          "created_at": feedback.created_at} if feedback else None),
            "allowed_transitions": self.incidents.allowed_transitions(actor, inc),
            "permissions": {
                "can_assign": is_admin and inc.status in (
                    IncidentStatus.CLASSIFIED, IncidentStatus.ASSIGNED, IncidentStatus.ACKNOWLEDGED,
                    IncidentStatus.IN_PROGRESS),
                "can_edit_priority": is_admin and inc.status != IncidentStatus.CLOSED,
                "can_edit_text": (is_admin or ActorKind.REPORTER in kinds) and inc.status not in DONE_STATUSES,
                "can_change_category": (is_admin or ActorKind.ASSIGNED_TECH in kinds) and inc.status != IncidentStatus.CLOSED,
                "can_request_info": (ActorKind.ASSIGNED_TECH in kinds or is_admin) and inc.status in (
                    IncidentStatus.ASSIGNED, IncidentStatus.ACKNOWLEDGED, IncidentStatus.IN_PROGRESS),
                "can_add_investigation_note": (ActorKind.ASSIGNED_TECH in kinds or is_admin) and inc.status != IncidentStatus.CLOSED,
                "can_reply": (ActorKind.REPORTER in kinds or is_admin) and inc.status != IncidentStatus.CLOSED,
                "can_give_feedback": (ActorKind.REPORTER in kinds and inc.status in DONE_STATUSES and feedback is None),
                "can_view_intelligence": actor.role in (Role.ADMIN, Role.TECHNICIAN),
            },
        })
        return base

    # ------------------------------------------------------------------ other shapes
    @staticmethod
    def note(note) -> dict:
        return {"id": note.id, "note_type": note.note_type.value, "body": note.body,
                "is_internal": note.is_internal, "created_at": note.created_at,
                "author": ({"id": note.author.id, "full_name": note.author.full_name,
                            "role": note.author.role.value} if note.author else None)}

    @staticmethod
    def timeline_entry(entry) -> dict:
        return {"id": entry.id, "action": entry.action, "description": entry.description,
                "actor_name": entry.actor.full_name if entry.actor else "System",
                "previous_state": entry.previous_state, "new_state": entry.new_state,
                "created_at": entry.created_at}

    @staticmethod
    def duplicate_item(match: dict) -> dict:
        inc = match["incident"]
        return {"number": inc.number, "title": inc.title, "status": inc.status.value,
                "priority": inc.priority.value, "similarity": match["similarity"],
                "reasons": match["reasons"], "created_at": inc.created_at}
