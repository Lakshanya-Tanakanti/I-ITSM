"""Priority calculation strategies (Strategy pattern).

The default algorithm is the one mandated by the specification:

    score = impact x urgency x business_criticality      (each 1..5, so 1..125)
    40-125 = P1 Critical | 20-39 = P2 High | 8-19 = P3 Medium | 1-7 = P4 Low
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.enums import Priority
from app.domain.exceptions import InvalidInputError


@dataclass(frozen=True)
class PriorityResult:
    score: int
    priority: Priority
    explanation: str


class PriorityStrategy(ABC):
    name: str = ""
    label: str = ""
    description: str = ""

    @abstractmethod
    def calculate(self, impact: int, urgency: int, criticality: int) -> PriorityResult:
        """Return the score and priority level for the three rating factors."""

    @staticmethod
    def validate(impact: int, urgency: int, criticality: int) -> None:
        for label, value in (("Impact", impact), ("Urgency", urgency), ("Business criticality", criticality)):
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
                raise InvalidInputError(f"{label} must be a whole number from 1 to 5.")


class AffectedUsersPolicy:
    """Turns the number of affected users into a minimum impact rating.

    The reporter's own impact rating is never lowered. When the head count implies a higher
    impact, the higher value is used as the impact factor of the priority score.

        users >= 1000 -> impact 5 | >= 250 -> 4 | >= 50 -> 3 | >= 10 -> 2 | fewer -> no floor
    """

    BANDS = ((1000, 5), (250, 4), (50, 3), (10, 2))

    @classmethod
    def floor_for(cls, affected_users) -> int:
        if not isinstance(affected_users, int) or isinstance(affected_users, bool) or affected_users < 0:
            return 1
        for minimum, impact in cls.BANDS:
            if affected_users >= minimum:
                return impact
        return 1

    @classmethod
    def adjust(cls, impact: int, affected_users) -> tuple:
        """Return (effective_impact, note). The note is None when nothing was changed."""
        floor = cls.floor_for(affected_users)
        if floor > impact:
            return floor, (f"Impact raised from {impact} to {floor} because {affected_users} users are affected.")
        return impact, None


class ScoreProductPriorityStrategy(PriorityStrategy):
    name = "product"
    label = "Impact x Urgency x Criticality"
    description = "Official rule: multiply the three ratings, then map the score to P1-P4."

    THRESHOLDS = ((40, Priority.P1), (20, Priority.P2), (8, Priority.P3), (1, Priority.P4))

    @classmethod
    def level_for_score(cls, score: int) -> Priority:
        """Map a raw score (1..125) to P1-P4 using the thresholds of BR-02."""
        if not isinstance(score, int) or score < 1 or score > 125:
            raise InvalidInputError("A priority score must be a whole number from 1 to 125.")
        for minimum, level in cls.THRESHOLDS:
            if score >= minimum:
                return level
        raise InvalidInputError("Score out of range.")  # pragma: no cover

    def calculate(self, impact: int, urgency: int, criticality: int) -> PriorityResult:
        self.validate(impact, urgency, criticality)
        score = impact * urgency * criticality
        level = self.level_for_score(score)
        return PriorityResult(
            score, level, f"{impact} x {urgency} x {criticality} = {score} -> {level.value} ({level.label})")


class WeightedPriorityStrategy(PriorityStrategy):
    """Alternative algorithm: weighted average of the three ratings.

    It exists to show that algorithms are interchangeable. Select it from
    Admin > Settings. Weights: impact 40%, urgency 35%, criticality 25%.
    """

    name = "weighted"
    label = "Weighted average"
    description = "Weighted average (40/35/25) of the ratings; P1 >= 4.0, P2 >= 3.0, P3 >= 2.0."

    def calculate(self, impact: int, urgency: int, criticality: int) -> PriorityResult:
        self.validate(impact, urgency, criticality)
        weighted = 0.40 * impact + 0.35 * urgency + 0.25 * criticality
        if weighted >= 4.0:
            level = Priority.P1
        elif weighted >= 3.0:
            level = Priority.P2
        elif weighted >= 2.0:
            level = Priority.P3
        else:
            level = Priority.P4
        score = round(weighted * 25)
        return PriorityResult(score, level, f"Weighted average {weighted:.2f} -> {level.value} ({level.label})")
