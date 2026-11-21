from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime
from app.domain.clock import utcnow
from app.models.incident import Incident
from app.models.user import User


class AuditLog(Base):
    """Append-only history of important actions (BR-15)."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_incident_time", "incident_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    incident_id: Mapped[Optional[int]] = mapped_column(ForeignKey("incidents.id"))
    action: Mapped[str] = mapped_column(String(80), index=True)
    previous_state: Mapped[Optional[str]] = mapped_column(String(30))
    new_state: Mapped[Optional[str]] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    extra: Mapped[Optional[str]] = mapped_column("metadata", Text)  # JSON text
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    actor: Mapped[Optional[User]] = relationship()
    incident: Mapped[Optional[Incident]] = relationship()


class AuditImmutableError(RuntimeError):
    pass


@event.listens_for(AuditLog, "before_update")
def _block_audit_update(mapper, connection, target):  # pragma: no cover - guard
    raise AuditImmutableError("Audit records are append-only and cannot be modified.")


@event.listens_for(AuditLog, "before_delete")
def _block_audit_delete(mapper, connection, target):  # pragma: no cover - guard
    raise AuditImmutableError("Audit records are append-only and cannot be deleted.")
