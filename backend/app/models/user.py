from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime
from app.domain.clock import utcnow
from app.domain.enums import Role
from app.utils.security import hash_password, verify_password


class User(Base):
    """An account. The password hash is private to this class (encapsulation)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[Optional[str]] = mapped_column(String(40), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    _password_hash: Mapped[str] = mapped_column("password_hash", String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False, length=20))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    technician_profile: Mapped[Optional["TechnicianProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        self._password_hash = hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self._password_hash)

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_technician(self) -> bool:
        return self.role == Role.TECHNICIAN

    @property
    def is_employee(self) -> bool:
        return self.role == Role.EMPLOYEE

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.email} {self.role.value}>"


class SupportTeam(Base):
    __tablename__ = "support_teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    lead: Mapped[Optional[User]] = relationship(foreign_keys=[lead_id])
    members: Mapped[list["TechnicianProfile"]] = relationship(back_populates="team")


class TechnicianProfile(Base):
    __tablename__ = "technician_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("support_teams.id"))
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    workload_limit: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="technician_profile")
    team: Mapped[Optional[SupportTeam]] = relationship(back_populates="members")
    skills: Mapped[list["TechnicianSkill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    def skill_map(self) -> dict:
        return {s.category_id: s.proficiency for s in self.skills}


class TechnicianSkill(Base):
    __tablename__ = "technician_skills"

    technician_id: Mapped[int] = mapped_column(
        ForeignKey("technician_profiles.id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("incident_categories.id"), primary_key=True
    )
    proficiency: Mapped[int] = mapped_column(Integer, default=3)

    profile: Mapped[TechnicianProfile] = relationship(back_populates="skills")
    category: Mapped["IncidentCategory"] = relationship()


from app.models.config_entities import IncidentCategory  # noqa: E402  (resolves the forward reference)
