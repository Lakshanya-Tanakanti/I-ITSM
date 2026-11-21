from typing import Optional

from sqlalchemy import func, select

from app.domain.enums import Priority
from app.models import IncidentCategory, Service, SlaPolicy, SystemSetting
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[IncidentCategory]):
    model = IncidentCategory

    def list(self, only_active: bool = False) -> list:
        stmt = select(IncidentCategory).order_by(IncidentCategory.name)
        if only_active:
            stmt = stmt.where(IncidentCategory.is_active.is_(True))
        return list(self.session.scalars(stmt).all())

    def get_by_name(self, name: str) -> Optional[IncidentCategory]:
        return self.session.scalar(
            select(IncidentCategory).where(func.lower(IncidentCategory.name) == name.strip().lower())
        )


class ServiceRepository(BaseRepository[Service]):
    model = Service

    def list(self, only_active: bool = False) -> list:
        stmt = select(Service).order_by(Service.name)
        if only_active:
            stmt = stmt.where(Service.is_active.is_(True))
        return list(self.session.scalars(stmt).all())

    def get_by_name(self, name: str) -> Optional[Service]:
        return self.session.scalar(select(Service).where(func.lower(Service.name) == name.strip().lower()))


class SlaPolicyRepository(BaseRepository[SlaPolicy]):
    model = SlaPolicy

    def list(self) -> list:
        return list(self.session.scalars(
            select(SlaPolicy).order_by(SlaPolicy.priority, SlaPolicy.service_id)
        ).all())

    def find_active(self, priority: Priority, service_id: Optional[int]) -> Optional[SlaPolicy]:
        """Service specific policy wins over the generic one (service_id NULL)."""
        if service_id is not None:
            specific = self.session.scalar(
                select(SlaPolicy).where(SlaPolicy.priority == priority, SlaPolicy.service_id == service_id,
                                        SlaPolicy.is_active.is_(True)).order_by(SlaPolicy.id.desc())
            )
            if specific:
                return specific
        return self.session.scalar(
            select(SlaPolicy).where(SlaPolicy.priority == priority, SlaPolicy.service_id.is_(None),
                                    SlaPolicy.is_active.is_(True)).order_by(SlaPolicy.id.desc())
        )


class SettingRepository:
    def __init__(self, session):
        self.session = session

    def get(self, key: str) -> Optional[SystemSetting]:
        return self.session.get(SystemSetting, key)

    def all(self) -> dict:
        return {s.key: s.value for s in self.session.scalars(select(SystemSetting)).all()}

    def set(self, key: str, value: str, now) -> SystemSetting:
        row = self.get(key)
        if row is None:
            row = SystemSetting(key=key, value=value, updated_at=now)
            self.session.add(row)
        else:
            row.value = value
            row.updated_at = now
        self.session.flush()
        return row
