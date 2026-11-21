"""FastAPI dependencies: database session, clock, service container, authentication and RBAC."""
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.enums import Role
from app.domain.exceptions import AuthenticationError, PermissionDeniedError
from app.models import User
from app.services.container import Container, build_container
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request):
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_clock(request: Request):
    return request.app.state.clock


def get_container(request: Request, db=Depends(get_db), clock=Depends(get_clock)) -> Container:
    return build_container(db, clock, request.app.state.settings)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    c: Container = Depends(get_container),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication is required.")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise AuthenticationError("Invalid authentication token.") from None
    user = c.repos.users.get(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("This account is not active.")
    return user


def require_roles(*roles: Role):
    """Dependency factory: only the listed roles may call the endpoint (checked on the server)."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("You do not have permission to perform this action.")
        return user

    return checker


require_admin = require_roles(Role.ADMIN)
require_technician = require_roles(Role.TECHNICIAN)
require_staff = require_roles(Role.ADMIN, Role.TECHNICIAN)
