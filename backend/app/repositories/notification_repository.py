from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import joinedload

from app.domain.enums import Channel
from app.models import AuditLog, Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def for_user(self, user_id: int, unread_only: bool = False, limit: int = 100,
                 channel: Channel = Channel.IN_APP) -> list:
        stmt = (select(Notification).where(Notification.recipient_id == user_id, Notification.channel == channel)
                .options(joinedload(Notification.incident)).order_by(Notification.created_at.desc(), Notification.id.desc())
                .limit(limit))
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        return list(self.session.scalars(stmt).unique().all())

    def unread_count(self, user_id: int) -> int:
        return self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == user_id, Notification.channel == Channel.IN_APP,
                Notification.is_read.is_(False))
        ) or 0

    def total_count(self, user_id: int) -> int:
        return self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == user_id, Notification.channel == Channel.IN_APP)
        ) or 0

    def mark_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        n = self.get(notification_id)
        if n is None or n.recipient_id != user_id:
            return None
        n.is_read = True
        self.session.flush()
        return n

    def mark_all_read(self, user_id: int) -> int:
        result = self.session.execute(
            update(Notification).where(Notification.recipient_id == user_id,
                                       Notification.channel == Channel.IN_APP,
                                       Notification.is_read.is_(False)).values(is_read=True)
        )
        return result.rowcount or 0

    def outbox(self, limit: int = 200) -> list:
        return list(self.session.scalars(
            select(Notification).where(Notification.channel == Channel.EMAIL)
            .options(joinedload(Notification.recipient), joinedload(Notification.incident))
            .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
        ).unique().all())

    def exists_for(self, incident_id: int, event_type: str, recipient_id: int) -> bool:
        return (self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.incident_id == incident_id, Notification.event_type == event_type,
                Notification.recipient_id == recipient_id)) or 0) > 0


class AuditRepository:
    """Append-only: there is intentionally no update or delete method."""

    def __init__(self, session):
        self.session = session

    def append(self, entry: AuditLog) -> AuditLog:
        self.session.add(entry)
        self.session.flush()
        return entry

    def search(self, incident_id=None, actor_id=None, action=None, from_dt=None, to_dt=None,
               q=None, page=1, page_size=50) -> tuple:
        conds = []
        if incident_id:
            conds.append(AuditLog.incident_id == incident_id)
        if actor_id:
            conds.append(AuditLog.actor_id == actor_id)
        if action:
            conds.append(AuditLog.action == action)
        if from_dt:
            conds.append(AuditLog.created_at >= from_dt)
        if to_dt:
            conds.append(AuditLog.created_at < to_dt)
        if q:
            conds.append(func.lower(AuditLog.description).like(f"%{q.strip().lower()}%"))
        total_stmt = select(func.count(AuditLog.id))
        stmt = select(AuditLog).options(joinedload(AuditLog.actor), joinedload(AuditLog.incident))
        for c in conds:
            total_stmt = total_stmt.where(c)
            stmt = stmt.where(c)
        total = self.session.scalar(total_stmt) or 0
        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(stmt).unique().all()), total

    def for_incident(self, incident_id: int) -> list:
        return list(self.session.scalars(
            select(AuditLog).where(AuditLog.incident_id == incident_id).options(joinedload(AuditLog.actor))
            .order_by(AuditLog.created_at, AuditLog.id)
        ).unique().all())

    def distinct_actions(self) -> list:
        return [a for a in self.session.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action)).all()]

    def count(self) -> int:
        return self.session.scalar(select(func.count(AuditLog.id))) or 0
