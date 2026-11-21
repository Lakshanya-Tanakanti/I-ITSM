from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime
from app.domain.clock import utcnow
from app.domain.enums import Channel
from app.models.incident import Incident
from app.models.user import User


class Notification(Base):
    """One delivered message. In-app and simulated e-mail share this table."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_recipient", "recipient_id", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    incident_id: Mapped[Optional[int]] = mapped_column(ForeignKey("incidents.id"))
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel, native_enum=False, length=20))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    event_type: Mapped[Optional[str]] = mapped_column(String(60))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_status: Mapped[str] = mapped_column(String(20), default="QUEUED")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    recipient: Mapped[User] = relationship()
    incident: Mapped[Optional[Incident]] = relationship()
