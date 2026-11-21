"""SLA calculation, tracking, violation detection and escalation."""
from datetime import datetime, timedelta
from typing import Optional

from app.domain.enums import (
    OPEN_STATUSES, EventType, IncidentStatus, Priority, SlaStatus, SlaType,
)
from app.domain.exceptions import MissingSlaConfigurationError
from app.models import Incident, SlaPolicy, SlaViolation
from app.services.base import BaseService, transactional

ESCALATION_LEVELS = {1: "Team Lead", 2: "System Administrator", 3: "IT Manager"}


def _fmt_minutes(minutes: float) -> str:
    minutes = int(round(minutes))
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest} min" if rest else f"{hours} h"


class SlaService(BaseService):
    def __init__(self, session, repos, bus, clock, settings_service):
        super().__init__(session, repos, bus, clock)
        self.settings_service = settings_service

    # ------------------------------------------------------------------ policy
    def select_policy(self, service_id: Optional[int], priority: Priority) -> SlaPolicy:
        policy = self.repos.sla_policies.find_active(priority, service_id)
        if policy is None:
            raise MissingSlaConfigurationError(
                f"No active SLA policy is configured for priority {Priority(priority).value}. "
                "Ask an administrator to add one."
            )
        return policy

    def apply_policy(self, incident: Incident, policy: SlaPolicy) -> None:
        """Deadlines start at incident creation and use calendar minutes (BR-05)."""
        incident.sla_policy = policy
        incident.sla_policy_id = policy.id
        incident.response_deadline = incident.created_at + timedelta(minutes=policy.response_minutes)
        incident.resolution_deadline = incident.created_at + timedelta(minutes=policy.resolution_minutes)

    # ------------------------------------------------------------------ description
    def _phase(self, incident: Incident, sla_type: SlaType, now: datetime) -> dict:
        policy = incident.sla_policy
        if sla_type == SlaType.RESPONSE:
            deadline, completed = incident.response_deadline, incident.acknowledged_at
            target = policy.response_minutes if policy else None
        else:
            deadline, completed = incident.resolution_deadline, incident.resolved_at
            target = policy.resolution_minutes if policy else None
        warning = policy.warning_percent if policy else 75
        violated = any(v.sla_type == sla_type for v in incident.violations)

        if deadline is None:
            return {"type": sla_type.value, "state": SlaStatus.ON_TRACK.value, "deadline": None,
                    "target_minutes": target, "completed_at": completed, "elapsed_percent": 0.0,
                    "remaining_seconds": None, "warning_percent": warning, "pending": completed is None}

        total = max((deadline - incident.created_at).total_seconds(), 1.0)
        end = completed or now
        elapsed = (end - incident.created_at).total_seconds()
        pct = max(0.0, elapsed / total * 100)
        pending = completed is None

        if violated or end > deadline:
            state = SlaStatus.BREACHED
        elif not pending:
            state = SlaStatus.MET
        elif pct >= warning:
            state = SlaStatus.AT_RISK
        else:
            state = SlaStatus.ON_TRACK
        remaining = (deadline - now).total_seconds() if pending else None
        return {
            "type": sla_type.value, "state": state.value, "deadline": deadline,
            "target_minutes": target, "completed_at": completed, "elapsed_percent": round(pct, 1),
            "remaining_seconds": int(remaining) if remaining is not None else None,
            "warning_percent": warning, "pending": pending,
        }

    def describe(self, incident: Incident, now: Optional[datetime] = None) -> dict:
        now = now or self.clock.now()
        response = self._phase(incident, SlaType.RESPONSE, now)
        resolution = self._phase(incident, SlaType.RESOLUTION, now)
        states = {response["state"], resolution["state"]}
        if SlaStatus.BREACHED.value in states:
            overall = SlaStatus.BREACHED
        elif SlaStatus.AT_RISK.value in states:
            overall = SlaStatus.AT_RISK
        elif response["state"] == SlaStatus.MET.value and resolution["state"] == SlaStatus.MET.value:
            overall = SlaStatus.MET
        else:
            overall = SlaStatus.ON_TRACK
        policy = incident.sla_policy
        return {
            "policy_name": policy.name if policy else None,
            "policy_id": incident.sla_policy_id,
            "warning_percent": policy.warning_percent if policy else 75,
            "response": response, "resolution": resolution, "overall": overall.value,
        }

    def refresh_status(self, incident: Incident, now: Optional[datetime] = None) -> SlaStatus:
        status = SlaStatus(self.describe(incident, now)["overall"])
        incident.sla_status = status
        return status

    # ------------------------------------------------------------------ violations
    def _record_violation(self, incident: Incident, sla_type: SlaType, deadline: datetime,
                          now: datetime, *, late_by: Optional[float] = None) -> bool:
        """One violation per incident per SLA type (BR-08). Returns True when newly recorded."""
        if self.repos.violations.exists(incident.id, sla_type):
            return False
        violation = SlaViolation(incident_id=incident.id, sla_type=sla_type, deadline_at=deadline, detected_at=now)
        self.repos.violations.add(violation)
        incident.violations.append(violation)
        label = "Response" if sla_type == SlaType.RESPONSE else "Resolution"
        if late_by is not None:
            text = (f"{label} SLA breached: completed {_fmt_minutes(late_by / 60)} after the deadline "
                    f"({deadline:%Y-%m-%d %H:%M} UTC).")
        else:
            text = f"{label} SLA breached: deadline {deadline:%Y-%m-%d %H:%M} UTC passed."
        self.emit(EventType.SLA_BREACHED, text, incident=incident, sla_type=sla_type.value,
                  deadline=deadline.isoformat())
        return True

    def on_acknowledged(self, incident: Incident, now: datetime) -> None:
        if incident.response_deadline and now > incident.response_deadline:
            self._record_violation(incident, SlaType.RESPONSE, incident.response_deadline, now,
                                   late_by=(now - incident.response_deadline).total_seconds())
        self.refresh_status(incident, now)

    def on_resolved(self, incident: Incident, now: datetime) -> None:
        if incident.resolution_deadline and now > incident.resolution_deadline:
            self._record_violation(incident, SlaType.RESOLUTION, incident.resolution_deadline, now,
                                   late_by=(now - incident.resolution_deadline).total_seconds())
        self.refresh_status(incident, now)

    # ------------------------------------------------------------------ monitoring
    def evaluate(self, incident: Incident, now: datetime, summary: dict) -> None:
        """Warn, record violations and escalate for one open incident."""
        info = self.describe(incident, now)
        for sla_type, phase in ((SlaType.RESPONSE, info["response"]), (SlaType.RESOLUTION, info["resolution"])):
            if not phase["pending"] or phase["deadline"] is None:
                continue
            if now > phase["deadline"]:
                if self._record_violation(incident, sla_type, phase["deadline"], now):
                    summary["breaches"] += 1
            elif phase["elapsed_percent"] >= phase["warning_percent"]:
                attr = "response_warned_at" if sla_type == SlaType.RESPONSE else "resolution_warned_at"
                if getattr(incident, attr) is None:
                    setattr(incident, attr, now)
                    label = "Response" if sla_type == SlaType.RESPONSE else "Resolution"
                    self.emit(
                        EventType.SLA_WARNING,
                        f"{label} SLA warning: {phase['elapsed_percent']:.0f}% of the allowed time used, "
                        f"{_fmt_minutes(phase['remaining_seconds'] / 60)} left.",
                        incident=incident, sla_type=sla_type.value,
                        elapsed_percent=phase["elapsed_percent"],
                    )
                    summary["warnings"] += 1
        self._maybe_escalate(incident, now, summary)
        self.refresh_status(incident, now)

    def _maybe_escalate(self, incident: Incident, now: datetime, summary: dict) -> None:
        """Automatic escalation: a P1/P2 incident nobody acknowledged climbs the chain
        Technician -> Team Lead -> System Administrator -> IT Manager."""
        if not self.settings_service.escalation_enabled():
            return
        if incident.priority not in (Priority.P1, Priority.P2):
            return
        if incident.acknowledged_at is not None or incident.status not in (
            IncidentStatus.ASSIGNED, IncidentStatus.CLASSIFIED
        ):
            return
        if incident.response_deadline is None or now <= incident.response_deadline:
            return
        if incident.escalation_level >= max(ESCALATION_LEVELS):
            return
        step = timedelta(minutes=max(incident.sla_policy.response_minutes if incident.sla_policy else 5, 1))
        reference = incident.escalated_at or incident.response_deadline
        if incident.escalation_level > 0 and now < reference + step:
            return
        incident.escalation_level += 1
        incident.escalated_at = now
        level_name = ESCALATION_LEVELS[incident.escalation_level]
        recipients = []
        if incident.escalation_level == 1:
            tech = incident.assigned_technician
            profile = tech.technician_profile if tech else None
            lead_id = profile.team.lead_id if profile and profile.team else None
            if lead_id and lead_id != incident.assigned_technician_id:
                recipients = [lead_id]  # a technician cannot escalate to themselves
        if not recipients:
            recipients = [a.id for a in self.repos.users.active_admins()]
        self.emit(
            EventType.INCIDENT_ESCALATED,
            f"Escalated to {level_name} (level {incident.escalation_level}): "
            f"{incident.priority.value} incident not acknowledged within its response time.",
            incident=incident, level=incident.escalation_level, level_name=level_name,
            recipient_ids=recipients,
        )
        summary["escalations"] += 1

    @transactional
    def run_check(self) -> dict:
        """Called by the background monitor every 60 seconds (and by tests)."""
        now = self.clock.now()
        summary = {"checked": 0, "warnings": 0, "breaches": 0, "escalations": 0, "checked_at": now}
        for incident in self.repos.incidents.list_open():
            summary["checked"] += 1
            self.evaluate(incident, now, summary)
        return summary

    # ------------------------------------------------------------------ lists
    def at_risk(self, limit: int = 50) -> list:
        now = self.clock.now()
        rows = []
        for inc in self.repos.incidents.list_open():
            info = self.describe(inc, now)
            if info["overall"] in (SlaStatus.AT_RISK.value, SlaStatus.BREACHED.value):
                rows.append((inc, info))
        order = {SlaStatus.BREACHED.value: 0, SlaStatus.AT_RISK.value: 1}
        rows.sort(key=lambda r: (order[r[1]["overall"]], r[0].priority.value, r[0].created_at))
        return rows[:limit]

    def violations(self, limit: int = 200) -> list:
        return self.repos.violations.list_all(limit)
