from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import ACTIVE_WORKLOAD_STATUSES, DONE_STATUSES, Role
from app.models import Incident, SupportTeam, TechnicianProfile, TechnicianSkill, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))

    def search(self, role: Optional[Role] = None, q: Optional[str] = None,
               is_active: Optional[bool] = None) -> list:
        stmt = select(User).options(selectinload(User.technician_profile))
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if q:
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(or_(func.lower(User.full_name).like(like),
                                  func.lower(User.email).like(like),
                                  func.lower(User.employee_code).like(like)))
        return list(self.session.scalars(stmt.order_by(User.full_name)).all())

    def active_admins(self) -> list:
        return list(self.session.scalars(
            select(User).where(User.role == Role.ADMIN, User.is_active.is_(True)).order_by(User.id)
        ).all())

    def count(self) -> int:
        return self.session.scalar(select(func.count(User.id))) or 0


class TeamRepository(BaseRepository[SupportTeam]):
    model = SupportTeam

    def get_by_name(self, name: str) -> Optional[SupportTeam]:
        return self.session.scalar(select(SupportTeam).where(func.lower(SupportTeam.name) == name.strip().lower()))

    def list_all(self) -> list:
        return list(self.session.scalars(select(SupportTeam).order_by(SupportTeam.name)).all())


class TechnicianRepository(BaseRepository[TechnicianProfile]):
    model = TechnicianProfile

    def get_by_user_id(self, user_id: int) -> Optional[TechnicianProfile]:
        return self.session.scalar(
            select(TechnicianProfile).where(TechnicianProfile.user_id == user_id)
            .options(selectinload(TechnicianProfile.skills).selectinload(TechnicianSkill.category))
        )

    def list_profiles(self) -> list:
        return list(self.session.scalars(
            select(TechnicianProfile)
            .options(selectinload(TechnicianProfile.skills).selectinload(TechnicianSkill.category),
                     selectinload(TechnicianProfile.user), selectinload(TechnicianProfile.team))
            .join(User, User.id == TechnicianProfile.user_id).order_by(User.full_name)
        ).all())

    def workload_map(self) -> dict:
        """user_id -> number of ASSIGNED/ACKNOWLEDGED/IN_PROGRESS incidents."""
        rows = self.session.execute(
            select(Incident.assigned_technician_id, func.count(Incident.id))
            .where(Incident.assigned_technician_id.is_not(None),
                   Incident.status.in_(ACTIVE_WORKLOAD_STATUSES))
            .group_by(Incident.assigned_technician_id)
        ).all()
        return {uid: n for uid, n in rows}

    def workload_for(self, user_id: int) -> int:
        return self.workload_map().get(user_id, 0)

    def service_experience_map(self, service_id: int) -> dict:
        rows = self.session.execute(
            select(Incident.assigned_technician_id, func.count(Incident.id))
            .where(Incident.service_id == service_id,
                   Incident.assigned_technician_id.is_not(None),
                   Incident.status.in_(DONE_STATUSES))
            .group_by(Incident.assigned_technician_id)
        ).all()
        return {uid: n for uid, n in rows}

    def replace_skills(self, profile: TechnicianProfile, skills: dict) -> None:
        """skills: {category_id: proficiency}"""
        existing = {s.category_id: s for s in profile.skills}
        for cid, skill in list(existing.items()):
            if cid not in skills:
                profile.skills.remove(skill)
        for cid, prof in skills.items():
            if cid in existing:
                existing[cid].proficiency = prof
            else:
                profile.skills.append(TechnicianSkill(category_id=cid, proficiency=prof))
        self.session.flush()
