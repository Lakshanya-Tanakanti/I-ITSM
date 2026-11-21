import re
from typing import Annotated, Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, StringConstraints

T = TypeVar("T")

Text = Annotated[str, StringConstraints(strip_whitespace=True)]
Rating = Annotated[int, "1 to 5"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list
    total: int
    page: int
    page_size: int
    pages: int


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    pages = max(1, -(-total // page_size)) if page_size else 1
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


class Message(BaseModel):
    message: str


PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


def validate_password_strength(value: str) -> str:
    if not PASSWORD_RULE.match(value):
        raise ValueError("Password must be 8-128 characters and contain at least one letter and one number.")
    return value
