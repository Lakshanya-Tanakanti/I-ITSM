from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.enums import Role
from app.schemas.common import ORMModel, validate_password_strength


class RegisterRequest(BaseModel):
    """Public registration. Any `role` sent by the client is ignored (extra fields are dropped)."""

    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str
    department: Optional[str] = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        return validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must have at least 2 characters.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    department: Optional[str] = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, v):
        return validate_password_strength(v)


class SkillOut(BaseModel):
    category_id: int
    category_name: str
    proficiency: int


class TechnicianProfileOut(BaseModel):
    id: int
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    experience_years: int
    is_available: bool
    workload_limit: int
    skills: list[SkillOut] = []


class UserOut(BaseModel):
    id: int
    employee_code: Optional[str] = None
    full_name: str
    email: str
    role: Role
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    technician_profile: Optional[TechnicianProfileOut] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str
    role: Role
    department: Optional[str] = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    department: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        return validate_password_strength(v) if v else v


class SkillIn(BaseModel):
    category_id: int
    proficiency: int = Field(ge=1, le=5)


class TechnicianProfileUpdate(BaseModel):
    team_id: Optional[int] = Field(default=None, description="0 removes the technician from the team")
    experience_years: Optional[int] = Field(default=None, ge=0, le=60)
    is_available: Optional[bool] = None
    workload_limit: Optional[int] = Field(default=None, ge=1, le=50)
    skills: Optional[list[SkillIn]] = None

    @field_validator("skills")
    @classmethod
    def _unique(cls, v):
        if v is not None and len({s.category_id for s in v}) != len(v):
            raise ValueError("Each skill category can only appear once.")
        return v


class AvailabilityUpdate(BaseModel):
    is_available: bool
