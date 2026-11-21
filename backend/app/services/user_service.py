from typing import Optional

from app.domain.enums import ACTIVE_WORKLOAD_STATUSES, EventType, Role
from app.domain.exceptions import (
    ConflictError, InvalidInputError, NotFoundError, PermissionDeniedError,
)
from app.models import TechnicianProfile, User
from app.services.auth_service import CODE_PREFIX, new_user
from app.services.base import BaseService, transactional


class UserService(BaseService):
    """Administrator functions for users, technician profiles and availability."""

    def __init__(self, session, repos, bus, clock, settings_service):
        super().__init__(session, repos, bus, clock)
        self.settings_service = settings_service

    def _get(self, user_id: int) -> User:
        user = self.repos.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def get_for_actor(self, actor: User, user_id: int) -> User:
        if actor.role != Role.ADMIN and actor.id != user_id:
            raise PermissionDeniedError("You can only view your own account.")
        return self._get(user_id)

    def list(self, actor: User, role=None, q=None, is_active=None) -> list:
        return self.repos.users.search(role, q, is_active)

    @transactional
    def create(self, actor: User, data: dict) -> User:
        role = Role(data["role"])
        user = new_user(
            self.repos, full_name=data["full_name"], email=data["email"], password=data["password"],
            role=role, department=data.get("department"), now=self.clock.now(),
            workload_limit=self.settings_service.all()["default_workload_limit"])
        self.emit(EventType.USER_CREATED, f"{actor.full_name} created {role.value.lower()} account {user.email}",
                  actor=actor, user_id=user.id, role=role.value)
        return user

    @transactional
    def update(self, actor: User, user_id: int, changes: dict) -> User:
        if actor.role != Role.ADMIN and actor.id != user_id:
            raise PermissionDeniedError("You can only edit your own profile.")
        user = self._get(user_id)
        is_admin = actor.role == Role.ADMIN
        restricted = {"role", "is_active", "email", "password"}
        if not is_admin and restricted & set(changes):
            raise PermissionDeniedError("Only administrators can change role, e-mail, status or password.")
        changed = []
        if changes.get("full_name"):
            user.full_name = changes["full_name"].strip()
            changed.append("full_name")
        if "department" in changes:
            user.department = (changes["department"] or "").strip() or None
            changed.append("department")
        if changes.get("email") and changes["email"].lower() != user.email:
            other = self.repos.users.get_by_email(changes["email"])
            if other and other.id != user.id:
                raise ConflictError("Another account already uses this e-mail address.")
            user.email = changes["email"].strip().lower()
            changed.append("email")
        if changes.get("password"):
            user.set_password(changes["password"])
            changed.append("password")
        if changes.get("role") and Role(changes["role"]) != user.role:
            self._change_role(actor, user, Role(changes["role"]))
            changed.append("role")
        if "is_active" in changes and changes["is_active"] is not None and changes["is_active"] != user.is_active:
            if changes["is_active"]:
                user.is_active = True
                changed.append("is_active")
            else:
                self._deactivate(actor, user)
                changed.append("is_active")
        user.updated_at = self.clock.now()
        if changed:
            self.emit(EventType.USER_UPDATED, f"{actor.full_name} updated {user.email}: {', '.join(changed)}",
                      actor=actor, user_id=user.id, fields=changed)
        return user

    def _change_role(self, actor: User, user: User, role: Role) -> None:
        if user.id == actor.id:
            raise ConflictError("You cannot change your own role.")
        if user.role == Role.TECHNICIAN and self.repos.technicians.workload_for(user.id) > 0:
            raise ConflictError("This technician still has active incidents. Reassign them first.")
        user.role = role
        user.employee_code = f"{CODE_PREFIX[role]}-{1000 + user.id}"
        if role == Role.TECHNICIAN and user.technician_profile is None:
            profile = TechnicianProfile(
                user=user, workload_limit=self.settings_service.all()["default_workload_limit"],
                created_at=self.clock.now())
            self.repos.technicians.add(profile)

    def _deactivate(self, actor: User, user: User) -> None:
        if user.id == actor.id:
            raise ConflictError("You cannot deactivate your own account.")
        if user.role == Role.ADMIN and len(self.repos.users.active_admins()) <= 1:
            raise ConflictError("The last active administrator cannot be deactivated.")
        if user.role == Role.TECHNICIAN and self.repos.technicians.workload_for(user.id) > 0:
            raise ConflictError("This technician still has active incidents. Reassign them before deactivating.")
        user.is_active = False

    @transactional
    def deactivate(self, actor: User, user_id: int) -> User:
        user = self._get(user_id)
        if not user.is_active:
            raise ConflictError("The account is already deactivated.")
        self._deactivate(actor, user)
        user.updated_at = self.clock.now()
        self.emit(EventType.USER_DEACTIVATED, f"{actor.full_name} deactivated {user.email}",
                  actor=actor, user_id=user.id)
        return user

    # ------------------------------------------------------------------ technician profile
    @transactional
    def update_technician_profile(self, actor: User, user_id: int, data: dict) -> User:
        user = self._get(user_id)
        if user.role != Role.TECHNICIAN or user.technician_profile is None:
            raise InvalidInputError("This user is not a technician.")
        profile = user.technician_profile
        if data.get("team_id") is not None:
            if data["team_id"] == 0:
                profile.team, profile.team_id = None, None
            else:
                team = self.repos.teams.get(data["team_id"])
                if team is None:
                    raise InvalidInputError("The selected team does not exist.")
                profile.team, profile.team_id = team, team.id
        for fld in ("experience_years", "is_available", "workload_limit"):
            if data.get(fld) is not None:
                setattr(profile, fld, data[fld])
        if data.get("skills") is not None:
            skills = {}
            for item in data["skills"]:
                cat = self.repos.categories.get(item["category_id"])
                if cat is None:
                    raise InvalidInputError(f"Category {item['category_id']} does not exist.")
                skills[cat.id] = item["proficiency"]
            self.repos.technicians.replace_skills(profile, skills)
        self.emit(EventType.TECHNICIAN_PROFILE_UPDATED,
                  f"{actor.full_name} updated the technician profile of {user.full_name}",
                  actor=actor, user_id=user.id)
        return user

    @transactional
    def set_availability(self, actor: User, is_available: bool) -> User:
        if actor.technician_profile is None:
            raise InvalidInputError("Only technicians have an availability setting.")
        actor.technician_profile.is_available = is_available
        self.emit(EventType.AVAILABILITY_CHANGED,
                  f"{actor.full_name} is now {'available' if is_available else 'unavailable'}", actor=actor,
                  is_available=is_available)
        return actor

    def workload(self, actor: User) -> list:
        loads = self.repos.technicians.workload_map()
        rows = []
        for profile in self.repos.technicians.list_profiles():
            user = profile.user
            if actor.role != Role.ADMIN and user.id != actor.id:
                continue
            active = loads.get(user.id, 0)
            rows.append({
                "technician_id": user.id, "name": user.full_name, "email": user.email,
                "team": profile.team.name if profile.team else None, "is_active": user.is_active,
                "is_available": profile.is_available, "active_incidents": active,
                "workload_limit": profile.workload_limit,
                "utilization_percent": round(active / profile.workload_limit * 100) if profile.workload_limit else 0,
                "experience_years": profile.experience_years,
                "skills": [s.category.name for s in profile.skills],
            })
        return rows
