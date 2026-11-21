from dataclasses import dataclass, field
from typing import Optional

from app.domain.enums import EventType
from app.domain.events import DomainEvent
from app.observers.base import EventObserver
from app.observers.channels import ChannelFactory


@dataclass
class Message:
    recipients: list
    subject: str
    body: str
    extra: dict = field(default_factory=dict)


class NotificationObserver(EventObserver):
    """Turns domain events into messages and sends them through every channel."""

    critical = False

    def __init__(self, repos, clock, channels: Optional[list] = None):
        self.repos = repos
        self.clock = clock
        self.channels = channels if channels is not None else ChannelFactory.default_channels()
        self._routes = {
            EventType.INCIDENT_CREATED: self._created,
            EventType.INCIDENT_CLASSIFIED: self._classified,
            EventType.PRIORITY_CHANGED: self._priority_changed,
            EventType.INCIDENT_ASSIGNED: self._assigned,
            EventType.INCIDENT_REASSIGNED: self._reassigned,
            EventType.NO_TECHNICIAN_AVAILABLE: self._no_technician,
            EventType.INCIDENT_ACKNOWLEDGED: self._acknowledged,
            EventType.INVESTIGATION_STARTED: self._investigation,
            EventType.INFO_REQUESTED: self._info_requested,
            EventType.INFO_PROVIDED: self._info_provided,
            EventType.INCIDENT_RESOLVED: self._resolved,
            EventType.INCIDENT_REOPENED: self._reopened,
            EventType.INCIDENT_VERIFIED: self._verified,
            EventType.INCIDENT_CLOSED: self._closed,
            EventType.FEEDBACK_SUBMITTED: self._feedback,
            EventType.SLA_WARNING: self._sla_warning,
            EventType.SLA_BREACHED: self._sla_breached,
            EventType.INCIDENT_ESCALATED: self._escalated,
        }

    # ------------------------------------------------------------------ entry point
    def handle(self, event: DomainEvent) -> None:
        builder = self._routes.get(event.type)
        if builder is None or event.incident is None:
            return
        message = builder(event)
        if message is None:
            return
        recipients = []
        for uid in message.recipients:
            if uid is None or uid in recipients:
                continue
            if uid == event.actor_id and event.type != EventType.INCIDENT_CREATED:
                continue  # do not notify people about their own actions
            recipients.append(uid)
        for uid in recipients:
            user = self.repos.users.get(uid)
            if user is None or not user.is_active:
                continue
            for channel in self.channels:
                channel.deliver(self.repos.notifications, user, event.incident_id, message.subject,
                                message.body, event.type.value, event.occurred_at)

    # ------------------------------------------------------------------ helpers
    def _admins(self) -> list:
        return [a.id for a in self.repos.users.active_admins()]

    @staticmethod
    def _tag(inc) -> str:
        return f"[{inc.number}]"

    # ------------------------------------------------------------------ message builders
    def _created(self, e):
        i = e.incident
        return Message(
            [i.reporter_id] + self._admins(),
            f"{self._tag(i)} Incident reported",
            f"Incident {i.number} \"{i.title}\" was reported for {i.service.name}. "
            f"Impact {i.impact}, urgency {i.urgency}.",
        )

    def _classified(self, e):
        i = e.incident
        cat = i.category.name if i.category else "Uncategorised"
        return Message(
            [i.reporter_id], f"{self._tag(i)} Classified as {cat}, priority {i.priority.value}",
            f"Your incident was classified as {cat} with priority {i.priority.value} "
            f"({i.priority.label}). Response is due by {i.response_deadline:%Y-%m-%d %H:%M} UTC and "
            f"resolution by {i.resolution_deadline:%Y-%m-%d %H:%M} UTC.",
        )

    def _priority_changed(self, e):
        i = e.incident
        return Message([i.reporter_id, i.assigned_technician_id], f"{self._tag(i)} Priority changed to {i.priority.value}",
                       e.description)

    def _assigned(self, e):
        i = e.incident
        tech = i.assigned_technician.full_name if i.assigned_technician else "a technician"
        # The reporter and the technician receive different texts.
        self._send_single(e, i.reporter_id, f"{self._tag(i)} Technician assigned",
                          f"Your incident {i.number} was assigned to {tech}.")
        return Message(
            [i.assigned_technician_id], f"{self._tag(i)} New incident assigned to you ({i.priority.value})",
            f"{i.number} \"{i.title}\" ({i.service.name}) has been assigned to you. "
            f"Please acknowledge it before {i.response_deadline:%Y-%m-%d %H:%M} UTC.",
        )

    def _send_single(self, e, uid, subject, body):
        if uid is None or (uid == e.actor_id):
            return
        user = self.repos.users.get(uid)
        if user is None or not user.is_active:
            return
        for channel in self.channels:
            channel.deliver(self.repos.notifications, user, e.incident_id, subject, body,
                            e.type.value, e.occurred_at)

    def _reassigned(self, e):
        i = e.incident
        prev = e.metadata.get("previous_technician_id")
        tech = i.assigned_technician.full_name if i.assigned_technician else "a technician"
        self._send_single(e, i.reporter_id, f"{self._tag(i)} Technician changed",
                          f"Your incident {i.number} is now handled by {tech}.")
        if prev and prev != i.assigned_technician_id:
            self._send_single(e, prev, f"{self._tag(i)} Incident reassigned",
                              f"{i.number} was reassigned to {tech}.")
        return Message([i.assigned_technician_id], f"{self._tag(i)} Incident reassigned to you ({i.priority.value})",
                       f"{i.number} \"{i.title}\" has been reassigned to you.")

    def _no_technician(self, e):
        i = e.incident
        return Message(self._admins(), f"{self._tag(i)} No eligible technician",
                       f"{i.number} could not be assigned automatically. {e.description}")

    def _acknowledged(self, e):
        i = e.incident
        return Message([i.reporter_id], f"{self._tag(i)} Technician acknowledged",
                       f"{i.assigned_technician.full_name if i.assigned_technician else 'A technician'} "
                       f"acknowledged your incident and will start investigating.")

    def _investigation(self, e):
        i = e.incident
        return Message([i.reporter_id], f"{self._tag(i)} Investigation started",
                       "Your incident is now being investigated.")

    def _info_requested(self, e):
        i = e.incident
        return Message([i.reporter_id], f"{self._tag(i)} More information needed",
                       f"The technician asked: {e.metadata.get('body', '')}")

    def _info_provided(self, e):
        i = e.incident
        return Message([i.assigned_technician_id], f"{self._tag(i)} Requester added information",
                       f"The reporter wrote: {e.metadata.get('body', '')}")

    def _resolved(self, e):
        i = e.incident
        summary = i.resolution.summary if i.resolution else ""
        return Message([i.reporter_id], f"{self._tag(i)} Incident resolved - please verify",
                       f"Your incident was resolved. Resolution: {summary} "
                       f"Please verify the fix or reopen the incident.")

    def _reopened(self, e):
        i = e.incident
        return Message([i.assigned_technician_id] + self._admins(), f"{self._tag(i)} Incident reopened",
                       e.description)

    def _verified(self, e):
        i = e.incident
        return Message([i.assigned_technician_id], f"{self._tag(i)} Resolution verified",
                       "The reporter confirmed that the fix works.")

    def _closed(self, e):
        i = e.incident
        return Message([i.reporter_id, i.assigned_technician_id], f"{self._tag(i)} Incident closed",
                       f"Incident {i.number} has been closed.")

    def _feedback(self, e):
        i = e.incident
        return Message([i.assigned_technician_id], f"{self._tag(i)} Feedback received", e.description)

    def _sla_warning(self, e):
        i = e.incident
        return Message([i.assigned_technician_id] + self._admins(),
                       f"{self._tag(i)} SLA warning ({e.metadata.get('sla_type', '')})", e.description)

    def _sla_breached(self, e):
        i = e.incident
        return Message([i.assigned_technician_id] + self._admins(),
                       f"{self._tag(i)} SLA BREACHED ({e.metadata.get('sla_type', '')})", e.description)

    def _escalated(self, e):
        i = e.incident
        return Message(e.metadata.get("recipient_ids", self._admins()),
                       f"{self._tag(i)} Escalation level {i.escalation_level}", e.description)
