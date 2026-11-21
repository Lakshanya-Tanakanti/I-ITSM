"""Incident lifecycle implemented with the State pattern.

Each lifecycle status is a class that knows which statuses may follow it,
who may trigger each transition and which extra data the transition needs.
`LifecycleManager` is the single entry point used by the services.

NEW -> CLASSIFIED -> ASSIGNED -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED
    -> VERIFIED -> CLOSED   (plus reopen and reassignment, see the rules below)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.enums import ActorKind, EventType, IncidentStatus
from app.domain.exceptions import InvalidInputError, InvalidTransitionError, PermissionDeniedError

S = IncidentStatus
K = ActorKind


@dataclass(frozen=True)
class TransitionRule:
    target: IncidentStatus
    allowed: frozenset
    event: EventType
    required_fields: tuple = ()
    description: str = ""


class IncidentState(ABC):
    """Abstract lifecycle state."""

    status: IncidentStatus

    @abstractmethod
    def rules(self) -> dict:
        """Return {target status: TransitionRule}."""

    def rule_for(self, target: IncidentStatus) -> TransitionRule | None:
        return self.rules().get(target)

    def next_statuses(self) -> list:
        return list(self.rules().keys())


class NewState(IncidentState):
    status = S.NEW

    def rules(self):
        return {
            S.CLASSIFIED: TransitionRule(
                S.CLASSIFIED, frozenset({K.SYSTEM}), EventType.INCIDENT_CLASSIFIED,
                description="System sets category, priority and SLA",
            )
        }


class ClassifiedState(IncidentState):
    status = S.CLASSIFIED

    def rules(self):
        return {
            S.ASSIGNED: TransitionRule(
                S.ASSIGNED, frozenset({K.SYSTEM, K.ADMIN}), EventType.INCIDENT_ASSIGNED,
                description="Assign an eligible technician",
            )
        }


class AssignedState(IncidentState):
    status = S.ASSIGNED

    def rules(self):
        return {
            S.ACKNOWLEDGED: TransitionRule(
                S.ACKNOWLEDGED, frozenset({K.ASSIGNED_TECH, K.ADMIN}),
                EventType.INCIDENT_ACKNOWLEDGED, description="Technician accepts the incident",
            ),
            # Re-assignment while the incident is still only ASSIGNED.
            S.ASSIGNED: TransitionRule(
                S.ASSIGNED, frozenset({K.ADMIN}), EventType.INCIDENT_REASSIGNED,
                description="Admin reassigns to another technician",
            ),
        }


class AcknowledgedState(IncidentState):
    status = S.ACKNOWLEDGED

    def rules(self):
        return {
            S.IN_PROGRESS: TransitionRule(
                S.IN_PROGRESS, frozenset({K.ASSIGNED_TECH, K.ADMIN}),
                EventType.INVESTIGATION_STARTED, description="Investigation starts",
            ),
            S.ASSIGNED: TransitionRule(
                S.ASSIGNED, frozenset({K.ADMIN}), EventType.INCIDENT_REASSIGNED,
                description="Admin reassigns to another technician",
            ),
        }


class InProgressState(IncidentState):
    status = S.IN_PROGRESS

    def rules(self):
        return {
            S.RESOLVED: TransitionRule(
                S.RESOLVED, frozenset({K.ASSIGNED_TECH, K.ADMIN}),
                EventType.INCIDENT_RESOLVED,
                required_fields=("resolution_summary", "root_cause"),
                description="Technician resolves with summary and root cause",
            ),
            S.ASSIGNED: TransitionRule(
                S.ASSIGNED, frozenset({K.ADMIN}), EventType.INCIDENT_REASSIGNED,
                description="Admin reassigns to another technician",
            ),
        }


class ResolvedState(IncidentState):
    status = S.RESOLVED

    def rules(self):
        return {
            S.VERIFIED: TransitionRule(
                S.VERIFIED, frozenset({K.REPORTER, K.ADMIN}), EventType.INCIDENT_VERIFIED,
                description="Reporter confirms the fix",
            ),
            S.IN_PROGRESS: TransitionRule(
                S.IN_PROGRESS, frozenset({K.REPORTER, K.ADMIN}), EventType.INCIDENT_REOPENED,
                required_fields=("reason",), description="Reporter reopens with a reason",
            ),
        }


class VerifiedState(IncidentState):
    status = S.VERIFIED

    def rules(self):
        return {
            S.CLOSED: TransitionRule(
                S.CLOSED, frozenset({K.REPORTER, K.ADMIN}), EventType.INCIDENT_CLOSED,
                description="Incident is closed",
            )
        }


class ClosedState(IncidentState):
    status = S.CLOSED

    def rules(self):
        return {}


_STATES = {
    S.NEW: NewState(),
    S.CLASSIFIED: ClassifiedState(),
    S.ASSIGNED: AssignedState(),
    S.ACKNOWLEDGED: AcknowledgedState(),
    S.IN_PROGRESS: InProgressState(),
    S.RESOLVED: ResolvedState(),
    S.VERIFIED: VerifiedState(),
    S.CLOSED: ClosedState(),
}


class StateFactory:
    @staticmethod
    def for_status(status: IncidentStatus) -> IncidentState:
        return _STATES[IncidentStatus(status)]


class LifecycleManager:
    """Validates and describes lifecycle transitions."""

    @staticmethod
    def validate(current, target, actor_kinds: set, payload: dict | None = None) -> TransitionRule:
        current = IncidentStatus(current)
        target = IncidentStatus(target)
        payload = payload or {}
        state = StateFactory.for_status(current)
        rule = state.rule_for(target)
        if rule is None:
            raise InvalidTransitionError(
                f"Cannot move an incident from {current.value} to {target.value}.",
                details={"from": current.value, "to": target.value,
                         "allowed": [s.value for s in state.next_statuses()]},
            )
        if not (set(actor_kinds) & set(rule.allowed)):
            raise PermissionDeniedError(
                f"You are not allowed to move an incident from {current.value} to {target.value}."
            )
        missing = [f for f in rule.required_fields if not str(payload.get(f) or "").strip()]
        if missing:
            raise InvalidInputError(
                "Missing required information: " + ", ".join(missing).replace("_", " ") + ".",
                details={"missing": missing},
            )
        return rule

    @staticmethod
    def allowed_next(current, actor_kinds: set) -> list:
        state = StateFactory.for_status(current)
        return [
            t.value for t, r in state.rules().items() if set(actor_kinds) & set(r.allowed)
        ]
