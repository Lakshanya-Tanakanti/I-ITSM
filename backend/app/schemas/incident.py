from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import IncidentStatus, NoteType


def _clean(v: str) -> str:
    return " ".join(v.split()) if v else v


class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    service_id: int = Field(gt=0)
    category_id: Optional[int] = Field(default=None, gt=0)
    impact: int = Field(ge=1, le=5)
    urgency: int = Field(ge=1, le=5)
    business_criticality: Optional[int] = Field(default=None, ge=1, le=5, description="Admin only override")
    affected_system: Optional[str] = Field(default=None, max_length=200)
    affected_users: Optional[int] = Field(default=None, ge=0, le=1_000_000)

    @field_validator("title")
    @classmethod
    def _title(cls, v):
        v = _clean(v)
        if len(v) < 5:
            raise ValueError("Title must have at least 5 characters.")
        return v

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Description must have at least 10 characters.")
        return v


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=5000)
    affected_system: Optional[str] = Field(default=None, max_length=200)
    affected_users: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    category_id: Optional[int] = Field(default=None, gt=0)
    service_id: Optional[int] = Field(default=None, gt=0)
    impact: Optional[int] = Field(default=None, ge=1, le=5)
    urgency: Optional[int] = Field(default=None, ge=1, le=5)
    business_criticality: Optional[int] = Field(default=None, ge=1, le=5)
    duplicate_of_number: Optional[str] = Field(default=None, max_length=30)


class TransitionRequest(BaseModel):
    to_status: IncidentStatus
    reason: Optional[str] = Field(default=None, max_length=2000)
    resolution_summary: Optional[str] = Field(default=None, max_length=5000)
    root_cause: Optional[str] = Field(default=None, max_length=2000)
    closure_note: Optional[str] = Field(default=None, max_length=2000)
    technician_id: Optional[int] = Field(default=None, gt=0)
    override: bool = False


class AssignRequest(BaseModel):
    technician_id: int = Field(gt=0)
    override: bool = Field(default=False, description="Admin acknowledges missing skill / workload limit")


class NoteCreate(BaseModel):
    note_type: NoteType = NoteType.COMMENT
    body: str = Field(min_length=1, max_length=5000)
    is_internal: Optional[bool] = None

    @field_validator("body")
    @classmethod
    def _body(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("The note cannot be empty.")
        return v


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class PriorityPreviewRequest(BaseModel):
    service_id: int = Field(gt=0)
    impact: int = Field(ge=1, le=5)
    urgency: int = Field(ge=1, le=5)
    affected_users: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    business_criticality: Optional[int] = Field(default=None, ge=1, le=5)


class CategorySuggestRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)


class DuplicateCheckRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    service_id: Optional[int] = None
    category_id: Optional[int] = None
