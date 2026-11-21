from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime
from app.domain.clock import utcnow
from app.domain.enums import IncidentStatus, NoteType, Priority, SlaStatus, SlaType
from app.models.config_entities import IncidentCategory, Service, SlaPolicy
from app.models.user import User


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("impact BETWEEN 1 AND 5", name="ck_incident_impact"),
        CheckConstraint("urgency BETWEEN 1 AND 5", name="ck_incident_urgency"),
        CheckConstraint("business_criticality BETWEEN 1 AND 5", name="ck_incident_criticality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("incident_categories.id"), index=True
    )
    category_source: Mapped[Optional[str]] = mapped_column(String(20))  # USER, AUTO, DEFAULT, ADMIN
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    affected_system: Mapped[Optional[str]] = mapped_column(String(200))
    affected_users: Mapped[Optional[int]] = mapped_column(Integer)

    impact: Mapped[int] = mapped_column(Integer)  # as reported
    # Impact actually used in the score (reported impact, raised by the affected-users policy).
    # NULL only on rows created before this column existed, which means "same as impact".
    effective_impact: Mapped[Optional[int]] = mapped_column(Integer)
    urgency: Mapped[int] = mapped_column(Integer)
    business_criticality: Mapped[int] = mapped_column(Integer)
    criticality_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_score: Mapped[int] = mapped_column(Integer)
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, native_enum=False, length=2), index=True
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(IncidentStatus, native_enum=False, length=30), index=True
    )
    assigned_technician_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), index=True
    )

    sla_policy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sla_policies.id"))
    response_deadline: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    resolution_deadline: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    verified_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    closed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    sla_status: Mapped[SlaStatus] = mapped_column(
        SAEnum(SlaStatus, native_enum=False, length=20), default=SlaStatus.ON_TRACK, index=True
    )
    response_warned_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    resolution_warned_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    awaiting_info: Mapped[bool] = mapped_column(Boolean, default=False)
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_of_id: Mapped[Optional[int]] = mapped_column(ForeignKey("incidents.id"))
    closure_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])
    assigned_technician: Mapped[Optional[User]] = relationship(foreign_keys=[assigned_technician_id])
    category: Mapped[Optional[IncidentCategory]] = relationship()
    service: Mapped[Service] = relationship()
    sla_policy: Mapped[Optional[SlaPolicy]] = relationship()
    duplicate_of: Mapped[Optional["Incident"]] = relationship(remote_side=[id])
    notes: Mapped[list["InvestigationNote"]] = relationship(
        back_populates="incident", order_by="InvestigationNote.created_at, InvestigationNote.id"
    )
    resolution: Mapped[Optional["Resolution"]] = relationship(back_populates="incident", uselist=False)
    feedback: Mapped[Optional["EmployeeFeedback"]] = relationship(
        back_populates="incident", uselist=False
    )
    violations: Mapped[list["SlaViolation"]] = relationship(back_populates="incident")

    @property
    def is_open(self) -> bool:
        return self.status in (
            IncidentStatus.NEW, IncidentStatus.CLASSIFIED, IncidentStatus.ASSIGNED,
            IncidentStatus.ACKNOWLEDGED, IncidentStatus.IN_PROGRESS,
        )


class InvestigationNote(Base):
    __tablename__ = "investigation_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    note_type: Mapped[NoteType] = mapped_column(SAEnum(NoteType, native_enum=False, length=30))
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="notes")
    author: Mapped[Optional[User]] = relationship()


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), unique=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    summary: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="resolution")
    technician: Mapped[User] = relationship()


class EmployeeFeedback(Base):
    __tablename__ = "employee_feedback"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), unique=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="feedback")


class SlaViolation(Base):
    __tablename__ = "sla_violations"
    __table_args__ = (UniqueConstraint("incident_id", "sla_type", name="uq_violation_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    sla_type: Mapped[SlaType] = mapped_column(SAEnum(SlaType, native_enum=False, length=20))
    deadline_at: Mapped[datetime] = mapped_column(UTCDateTime)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="violations")
