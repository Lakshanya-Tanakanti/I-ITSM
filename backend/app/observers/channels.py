"""Notification channels. Adding SMS or push later means adding one class here."""
import logging
from abc import ABC, abstractmethod

from app.domain.enums import Channel
from app.models import Notification

logger = logging.getLogger("iitsm.notifications")


class NotificationChannel(ABC):
    channel: Channel

    @abstractmethod
    def deliver(self, repo, recipient, incident_id, subject, body, event_type, now) -> Notification:
        """Deliver one message and return the stored record."""


class InAppChannel(NotificationChannel):
    channel = Channel.IN_APP

    def deliver(self, repo, recipient, incident_id, subject, body, event_type, now):
        return repo.add(Notification(
            recipient_id=recipient.id, incident_id=incident_id, channel=self.channel,
            subject=subject, body=body, event_type=event_type, is_read=False,
            delivery_status="DELIVERED", created_at=now,
        ))


class SimulatedEmailChannel(NotificationChannel):
    """Adapter for an e-mail gateway. No mail is really sent: the message is
    written to the outbox table and to the log so it can be shown in the UI."""

    channel = Channel.EMAIL

    def deliver(self, repo, recipient, incident_id, subject, body, event_type, now):
        logger.info("[SIMULATED EMAIL] to=%s subject=%s", recipient.email, subject)
        return repo.add(Notification(
            recipient_id=recipient.id, incident_id=incident_id, channel=self.channel,
            subject=subject, body=body, event_type=event_type, is_read=True,
            delivery_status="SENT", created_at=now,
        ))


class ChannelFactory:
    _registry: dict = {}

    @classmethod
    def register(cls, channel_cls: type) -> None:
        cls._registry[channel_cls.channel] = channel_cls

    @classmethod
    def default_channels(cls) -> list:
        return [c() for c in cls._registry.values()]


ChannelFactory.register(InAppChannel)
ChannelFactory.register(SimulatedEmailChannel)
