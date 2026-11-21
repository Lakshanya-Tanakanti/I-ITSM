from app.domain.exceptions import NotFoundError
from app.services.base import BaseService, transactional


class NotificationService(BaseService):
    def list_for(self, user, unread_only: bool = False, limit: int = 100) -> dict:
        items = self.repos.notifications.for_user(user.id, unread_only=unread_only, limit=limit)
        return {"items": items, "unread_count": self.repos.notifications.unread_count(user.id),
                "total": self.repos.notifications.total_count(user.id)}

    @transactional
    def mark_read(self, user, notification_id: int):
        n = self.repos.notifications.mark_read(notification_id, user.id)
        if n is None:
            raise NotFoundError("Notification not found.")
        return n

    @transactional
    def mark_all_read(self, user) -> int:
        return self.repos.notifications.mark_all_read(user.id)

    def outbox(self, limit: int = 200) -> list:
        return self.repos.notifications.outbox(limit)
