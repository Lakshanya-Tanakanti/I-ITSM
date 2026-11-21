"""Generic repository (Repository pattern). Only repositories talk to the database."""
from typing import Generic, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: type

    def __init__(self, session: Session):
        self.session = session

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id) -> Optional[T]:
        return self.session.get(self.model, entity_id)

    def list_all(self) -> list:
        return list(self.session.scalars(select(self.model)).all())

    def flush(self) -> None:
        self.session.flush()
