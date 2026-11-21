from app.config import Settings
from app.domain.enums import EventType
from app.domain.exceptions import InvalidInputError
from app.services.base import BaseService, transactional
from app.strategies.factory import StrategyFactory


class SettingsService(BaseService):
    """System settings stored in the database (admin configurable)."""

    def __init__(self, session, repos, bus, clock, app_settings: Settings):
        super().__init__(session, repos, bus, clock)
        self.app_settings = app_settings

    def defaults(self) -> dict:
        return {
            "assignment_strategy": "skill_then_load",
            "priority_strategy": "product",
            "auto_assign": "true",
            "escalation_enabled": "true",
            "affected_users_adjustment": "true",
            "duplicate_threshold": str(self.app_settings.duplicate_similarity_threshold),
            "default_workload_limit": str(self.app_settings.default_technician_workload_limit),
        }

    def all(self) -> dict:
        values = {**self.defaults(), **self.repos.settings.all()}
        return {
            "assignment_strategy": values["assignment_strategy"],
            "priority_strategy": values["priority_strategy"],
            "auto_assign": values["auto_assign"].lower() == "true",
            "escalation_enabled": values["escalation_enabled"].lower() == "true",
            "affected_users_adjustment": values["affected_users_adjustment"].lower() == "true",
            "duplicate_threshold": float(values["duplicate_threshold"]),
            "default_workload_limit": int(values["default_workload_limit"]),
        }

    def options(self) -> dict:
        return {
            "assignment_strategies": StrategyFactory.assignment_options(),
            "priority_strategies": StrategyFactory.priority_options(),
        }

    # -- typed accessors -------------------------------------------------
    def assignment_strategy(self):
        return StrategyFactory.assignment(self.all()["assignment_strategy"])

    def priority_strategy(self):
        return StrategyFactory.priority(self.all()["priority_strategy"])

    def auto_assign(self) -> bool:
        return self.all()["auto_assign"]

    def escalation_enabled(self) -> bool:
        return self.all()["escalation_enabled"]

    def affected_users_adjustment(self) -> bool:
        return self.all()["affected_users_adjustment"]

    def duplicate_threshold(self) -> float:
        return self.all()["duplicate_threshold"]

    # -- update ----------------------------------------------------------
    @transactional
    def update(self, actor, changes: dict) -> dict:
        before = self.all()
        now = self.clock.now()
        for key, value in changes.items():
            if value is None:
                continue
            if key == "assignment_strategy":
                StrategyFactory.assignment(value)  # validates
            elif key == "priority_strategy":
                StrategyFactory.priority(value)
            elif key == "duplicate_threshold":
                if not 0.1 <= float(value) <= 1.0:
                    raise InvalidInputError("Duplicate threshold must be between 0.1 and 1.0.")
            elif key == "default_workload_limit":
                if not 1 <= int(value) <= 50:
                    raise InvalidInputError("Workload limit must be between 1 and 50.")
            elif key not in ("auto_assign", "escalation_enabled", "affected_users_adjustment"):
                raise InvalidInputError(f"Unknown setting '{key}'.")
            stored = str(value).lower() if isinstance(value, bool) else str(value)
            self.repos.settings.set(key, stored, now)
        after = self.all()
        diff = {k: {"from": before[k], "to": after[k]} for k in after if before[k] != after[k]}
        if diff:
            self.emit(EventType.CONFIG_CHANGED, "System settings changed: " +
                      ", ".join(f"{k} {v['from']} -> {v['to']}" for k, v in diff.items()),
                      actor=actor, changes=diff)
        return after
