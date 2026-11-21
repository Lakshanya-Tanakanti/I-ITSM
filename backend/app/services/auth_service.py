from typing import Optional

from app.domain.enums import ACTIVE_WORKLOAD_STATUSES, EventType, Role
from app.domain.exceptions import AuthenticationError, DuplicateResourceError, InvalidInputError
from app.models import TechnicianProfile, User
from app.services.base import BaseService, transactional
from app.utils.security import create_access_token

CODE_PREFIX = {Role.EMPLOYEE: "EMP", Role.TECHNICIAN: "TECH", Role.ADMIN: "ADM"}


def new_user(repos, *, full_name: str, email: str, password: str, role: Role,
             department: Optional[str], now, workload_limit: int = 5) -> User:
    """Factory for users of every role (also creates the technician profile)."""
    if repos.users.get_by_email(email):
        raise DuplicateResourceError("An account with this e-mail address already exists.")
    user = User(full_name=full_name.strip(), email=email.strip().lower(), role=role,
                department=(department or "").strip() or None, is_active=True,
                created_at=now, updated_at=now)
    user.set_password(password)
    repos.users.add(user)
    user.employee_code = f"{CODE_PREFIX[role]}-{1000 + user.id}"
    if role == Role.TECHNICIAN:
        profile = TechnicianProfile(user=user, workload_limit=workload_limit, created_at=now)
        repos.technicians.add(profile)
    return user


class AuthService(BaseService):
    def __init__(self, session, repos, bus, clock, settings_service):
        super().__init__(session, repos, bus, clock)
        self.settings_service = settings_service

    @transactional
    def register(self, full_name: str, email: str, password: str, department: Optional[str]) -> User:
        """Public registration. The role is always EMPLOYEE (never taken from input)."""
        user = new_user(self.repos, full_name=full_name, email=email, password=password,
                        role=Role.EMPLOYEE, department=department, now=self.clock.now())
        self.emit(EventType.USER_REGISTERED, f"{user.full_name} registered as an employee", actor=user,
                  user_id=user.id)
        return user

    def login(self, email: str, password: str) -> tuple:
        user = self.repos.users.get_by_email(email)
        if user is None or not user.check_password(password):
            self.emit(EventType.USER_LOGIN_FAILED, f"Failed sign-in attempt for {email.strip().lower()}",
                      actor=user, email=email.strip().lower())
            self.session.commit()
            raise AuthenticationError("Incorrect e-mail address or password.")
        if not user.is_active:
            self.emit(EventType.USER_LOGIN_FAILED, f"Sign-in blocked: account {user.email} is deactivated",
                      actor=user)
            self.session.commit()
            raise AuthenticationError("This account has been deactivated. Contact an administrator.")
        self.emit(EventType.USER_LOGIN, f"{user.full_name} signed in", actor=user, role=user.role.value)
        self.session.commit()
        return create_access_token(user.id, user.role.value), user

    @transactional
    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not user.check_password(current_password):
            raise AuthenticationError("The current password is incorrect.")
        if current_password == new_password:
            raise InvalidInputError("The new password must be different from the current one.")
        user.set_password(new_password)
        user.updated_at = self.clock.now()
        self.emit(EventType.PASSWORD_CHANGED, f"{user.full_name} changed their password", actor=user)

    @transactional
    def update_profile(self, user: User, changes: dict) -> User:
        changed = []
        for fld in ("full_name", "department"):
            if fld in changes and changes[fld] is not None:
                value = changes[fld].strip() or None
                if fld == "full_name" and not value:
                    raise InvalidInputError("Name cannot be empty.")
                if getattr(user, fld) != value:
                    setattr(user, fld, value)
                    changed.append(fld)
        if changed:
            user.updated_at = self.clock.now()
            self.emit(EventType.USER_UPDATED, f"{user.full_name} updated their profile ({', '.join(changed)})",
                      actor=user, fields=changed)
        return user
