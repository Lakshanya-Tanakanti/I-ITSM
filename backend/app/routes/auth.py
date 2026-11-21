from fastapi import APIRouter, Depends

from app.middleware.dependencies import get_container, get_current_user
from app.models import User
from app.schemas.common import Message
from app.schemas.user import (
    ChangePasswordRequest, LoginRequest, ProfileUpdate, RegisterRequest, TokenOut, UserOut,
)
from app.services.container import Container
from app.services.presenter import user_full

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, c: Container = Depends(get_container)):
    """Public registration. Always creates an EMPLOYEE account."""
    user = c.auth.register(body.full_name, body.email, body.password, body.department)
    return user_full(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, c: Container = Depends(get_container)):
    token, user = c.auth.login(body.email, body.password)
    return {"access_token": token, "token_type": "bearer", "user": user_full(user)}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_full(user)


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return user_full(c.auth.update_profile(user, body.model_dump(exclude_unset=True)))


@router.post("/change-password", response_model=Message)
def change_password(body: ChangePasswordRequest, user: User = Depends(get_current_user),
                    c: Container = Depends(get_container)):
    c.auth.change_password(user, body.current_password, body.new_password)
    return {"message": "Password changed."}
