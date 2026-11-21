"""Factory / registry that creates strategies by name.

New algorithms are added with `register_*` and need no change anywhere else.
"""
from app.domain.exceptions import InvalidInputError
from app.strategies.assignment import (
    AssignmentStrategy, LoadBasedStrategy, SkillBasedStrategy, SkillThenLoadStrategy,
)
from app.strategies.priority import (
    PriorityStrategy, ScoreProductPriorityStrategy, WeightedPriorityStrategy,
)


class StrategyFactory:
    _assignment: dict = {}
    _priority: dict = {}

    @classmethod
    def register_assignment(cls, strategy_cls: type) -> None:
        cls._assignment[strategy_cls.name] = strategy_cls

    @classmethod
    def register_priority(cls, strategy_cls: type) -> None:
        cls._priority[strategy_cls.name] = strategy_cls

    @classmethod
    def assignment(cls, name: str) -> AssignmentStrategy:
        try:
            return cls._assignment[name]()
        except KeyError:
            raise InvalidInputError(f"Unknown assignment strategy '{name}'.") from None

    @classmethod
    def priority(cls, name: str) -> PriorityStrategy:
        try:
            return cls._priority[name]()
        except KeyError:
            raise InvalidInputError(f"Unknown priority strategy '{name}'.") from None

    @classmethod
    def assignment_options(cls) -> list:
        return [{"name": c.name, "label": c.label, "description": c.description}
                for c in cls._assignment.values()]

    @classmethod
    def priority_options(cls) -> list:
        return [{"name": c.name, "label": c.label, "description": c.description}
                for c in cls._priority.values()]


for _cls in (SkillBasedStrategy, LoadBasedStrategy, SkillThenLoadStrategy):
    StrategyFactory.register_assignment(_cls)
for _cls in (ScoreProductPriorityStrategy, WeightedPriorityStrategy):
    StrategyFactory.register_priority(_cls)
