from typing import Optional

from pydantic import BaseModel, Field

from app.domain.enums import Priority


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=1000)
    keywords: Optional[str] = Field(default=None, max_length=2000, description="Comma separated")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=1000)
    keywords: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    is_active: bool


class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    business_criticality: int = Field(ge=1, le=5)


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    business_criticality: Optional[int] = Field(default=None, ge=1, le=5)
    is_active: Optional[bool] = None


class ServiceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    business_criticality: int
    is_active: bool


class SlaPolicyIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    priority: Priority
    service_id: Optional[int] = Field(default=None, gt=0)
    response_minutes: int = Field(gt=0, le=525600)
    resolution_minutes: int = Field(gt=0, le=525600)
    warning_percent: int = Field(default=75, ge=1, le=99)


class SlaPolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    priority: Optional[Priority] = None
    service_id: Optional[int] = None
    response_minutes: Optional[int] = Field(default=None, gt=0, le=525600)
    resolution_minutes: Optional[int] = Field(default=None, gt=0, le=525600)
    warning_percent: Optional[int] = Field(default=None, ge=1, le=99)
    is_active: Optional[bool] = None


class SlaPolicyOut(BaseModel):
    id: int
    name: str
    priority: Priority
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    response_minutes: int
    resolution_minutes: int
    warning_percent: int
    is_active: bool


class TeamIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    lead_id: Optional[int] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    lead_id: Optional[int] = None
    is_active: Optional[bool] = None


class TeamOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    lead_id: Optional[int] = None
    lead_name: Optional[str] = None
    is_active: bool
    member_count: int = 0


class SettingsUpdate(BaseModel):
    assignment_strategy: Optional[str] = None
    priority_strategy: Optional[str] = None
    auto_assign: Optional[bool] = None
    escalation_enabled: Optional[bool] = None
    affected_users_adjustment: Optional[bool] = None
    duplicate_threshold: Optional[float] = Field(default=None, ge=0.1, le=1.0)
    default_workload_limit: Optional[int] = Field(default=None, ge=1, le=50)
