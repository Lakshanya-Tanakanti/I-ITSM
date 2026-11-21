"""Technician assignment: eligibility policy and ranking strategies.

* `EligibilityPolicy` decides who may be assigned at all (BR-09, BR-10, BR-11).
* `AssignmentStrategy` implementations rank the eligible technicians.
  They are interchangeable at run time (Strategy pattern).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from app.domain.enums import Priority


@dataclass
class TechnicianCandidate:
    """Snapshot of a technician used by the algorithms (no ORM dependency)."""

    user_id: int
    name: str
    is_active: bool
    is_available: bool
    workload_limit: int
    active_workload: int
    experience_years: int
    skills: dict  # category_id -> proficiency 1..5
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    service_experience: int = 0  # resolved incidents on the same service

    @property
    def load_ratio(self) -> float:
        return self.active_workload / self.workload_limit if self.workload_limit else 1.0


@dataclass
class AssignmentContext:
    category_id: Optional[int]
    category_name: str
    priority: Priority
    service_id: Optional[int] = None


@dataclass
class Ineligibility:
    code: str  # INACTIVE | UNAVAILABLE | NO_SKILL | AT_LIMIT
    message: str


@dataclass
class Recommendation:
    technician_id: int
    name: str
    score: float
    rank: int = 0
    reasons: list = field(default_factory=list)
    factors: dict = field(default_factory=dict)
    team_name: Optional[str] = None


class EligibilityPolicy:
    """Hard rules: only technicians that pass can be assigned automatically."""

    def check(self, tech: TechnicianCandidate, ctx: AssignmentContext) -> list:
        problems = []
        if not tech.is_active:
            problems.append(Ineligibility("INACTIVE", "Account is deactivated"))
        if not tech.is_available:
            problems.append(Ineligibility("UNAVAILABLE", "Marked unavailable"))
        if ctx.category_id is not None and ctx.category_id not in tech.skills:
            problems.append(Ineligibility("NO_SKILL", f"Lacks the {ctx.category_name} skill"))
        if tech.active_workload >= tech.workload_limit:
            problems.append(
                Ineligibility("AT_LIMIT", f"At workload limit ({tech.active_workload}/{tech.workload_limit})")
            )
        return problems


class AssignmentStrategy(ABC):
    name: str = ""
    label: str = ""
    description: str = ""

    def rank(self, eligible: list, ctx: AssignmentContext) -> list:
        """Return Recommendation objects, best first, with rank numbers filled in."""
        scored = [self._score(t, ctx) for t in eligible]
        scored.sort(key=lambda r: (-r.score, r.name.lower(), r.technician_id))
        for i, rec in enumerate(scored, start=1):
            rec.rank = i
        return scored

    @abstractmethod
    def _score(self, tech: TechnicianCandidate, ctx: AssignmentContext) -> Recommendation:
        """Score a single technician and explain the score."""

    @staticmethod
    def _base_reasons(tech: TechnicianCandidate, ctx: AssignmentContext) -> list:
        prof = tech.skills.get(ctx.category_id, 0)
        reasons = []
        if prof:
            reasons.append(f"{ctx.category_name} skill proficiency {prof}/5")
        reasons.append(f"{tech.experience_years} year(s) of experience")
        if tech.service_experience:
            reasons.append(f"Resolved {tech.service_experience} earlier incident(s) on this service")
        reasons.append(f"Workload {tech.active_workload}/{tech.workload_limit}")
        return reasons


class SkillBasedStrategy(AssignmentStrategy):
    name = "skill_based"
    label = "Skill based"
    description = "Best skill proficiency first, then experience and service history. Workload only breaks ties."

    def _score(self, tech, ctx):
        prof = tech.skills.get(ctx.category_id, 0)
        score = prof * 20 + min(tech.experience_years, 10) * 2 + min(tech.service_experience, 5) * 2
        score -= tech.active_workload * 0.5  # tiny tie-breaker
        return Recommendation(
            tech.user_id, tech.name, round(score, 2),
            reasons=self._base_reasons(tech, ctx),
            factors={"proficiency": prof, "experience_years": tech.experience_years,
                     "service_experience": tech.service_experience,
                     "workload": tech.active_workload, "workload_limit": tech.workload_limit},
            team_name=tech.team_name,
        )


class LoadBasedStrategy(AssignmentStrategy):
    name = "load_based"
    label = "Load based"
    description = "Least loaded eligible technician first (balances work). Skill only breaks ties."

    def _score(self, tech, ctx):
        prof = tech.skills.get(ctx.category_id, 0)
        score = (1 - tech.load_ratio) * 100 + prof * 1.0 + min(tech.experience_years, 10) * 0.1
        reasons = self._base_reasons(tech, ctx)
        reasons.insert(0, f"Free capacity {tech.workload_limit - tech.active_workload} of {tech.workload_limit}")
        return Recommendation(
            tech.user_id, tech.name, round(score, 2), reasons=reasons,
            factors={"proficiency": prof, "experience_years": tech.experience_years,
                     "service_experience": tech.service_experience,
                     "workload": tech.active_workload, "workload_limit": tech.workload_limit},
            team_name=tech.team_name,
        )


class SkillThenLoadStrategy(AssignmentStrategy):
    """Balanced default: skill and experience matter most, workload is a strong secondary factor.

    Critical incidents (P1/P2) put more weight on skill and experience.
    """

    name = "skill_then_load"
    label = "Skill then load (balanced)"
    description = "Weighted blend of skill, experience, service history and free capacity."

    def _score(self, tech, ctx):
        prof = tech.skills.get(ctx.category_id, 0)
        critical = ctx.priority in (Priority.P1, Priority.P2)
        skill_weight = 22 if critical else 18
        exp_weight = 2.0 if critical else 1.0
        score = (
            prof * skill_weight
            + min(tech.experience_years, 10) * exp_weight
            + min(tech.service_experience, 5) * 2
            + (1 - tech.load_ratio) * 30
        )
        reasons = self._base_reasons(tech, ctx)
        if critical:
            reasons.append("Critical priority: skill and experience weighted higher")
        return Recommendation(
            tech.user_id, tech.name, round(score, 2), reasons=reasons,
            factors={"proficiency": prof, "experience_years": tech.experience_years,
                     "service_experience": tech.service_experience,
                     "workload": tech.active_workload, "workload_limit": tech.workload_limit},
            team_name=tech.team_name,
        )
