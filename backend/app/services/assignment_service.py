"""Technician recommendation and assignment validation."""
from typing import Optional

from app.domain.enums import Role
from app.domain.exceptions import (
    MissingSkillError, TechnicianUnavailableError, WorkloadExceededError,
)
from app.models import Incident, User
from app.strategies.assignment import (
    AssignmentContext, EligibilityPolicy, TechnicianCandidate,
)
from app.strategies.factory import StrategyFactory


class AssignmentService:
    def __init__(self, repos, settings_service):
        self.repos = repos
        self.settings_service = settings_service
        self.policy = EligibilityPolicy()

    # ------------------------------------------------------------------ building blocks
    def _context(self, incident: Incident) -> AssignmentContext:
        return AssignmentContext(
            category_id=incident.category_id,
            category_name=incident.category.name if incident.category else "required",
            priority=incident.priority, service_id=incident.service_id,
        )

    def _candidates(self, incident: Incident) -> list:
        workload = self.repos.technicians.workload_map()
        service_exp = self.repos.technicians.service_experience_map(incident.service_id)
        result = []
        for profile in self.repos.technicians.list_profiles():
            user = profile.user
            if user.role != Role.TECHNICIAN:
                continue
            result.append(TechnicianCandidate(
                user_id=user.id, name=user.full_name, is_active=user.is_active,
                is_available=profile.is_available, workload_limit=profile.workload_limit,
                active_workload=workload.get(user.id, 0), experience_years=profile.experience_years,
                skills=profile.skill_map(), team_id=profile.team_id,
                team_name=profile.team.name if profile.team else None,
                service_experience=service_exp.get(user.id, 0),
            ))
        return result

    # ------------------------------------------------------------------ public API
    def recommend(self, incident: Incident, strategy_name: Optional[str] = None) -> dict:
        strategy = (StrategyFactory.assignment(strategy_name) if strategy_name
                    else self.settings_service.assignment_strategy())
        ctx = self._context(incident)
        eligible, ineligible = [], []
        for cand in self._candidates(incident):
            if cand.user_id == incident.assigned_technician_id:
                continue  # already holds the incident
            problems = self.policy.check(cand, ctx)
            if problems:
                ineligible.append({
                    "technician_id": cand.user_id, "name": cand.name,
                    "reasons": [p.message for p in problems], "codes": [p.code for p in problems],
                })
            else:
                eligible.append(cand)
        ranked = strategy.rank(eligible, ctx)
        return {
            "strategy": {"name": strategy.name, "label": strategy.label, "description": strategy.description},
            "eligible": ranked,
            "ineligible": ineligible,
        }

    def ensure_assignable(self, incident: Incident, technician: User, override: bool = False) -> list:
        """Raise a precise error when the technician cannot take the incident.

        With `override=True` (admin only) workload and skill problems are accepted
        but returned so that the caller can write them to the audit log (BR-11:
        never silently assign without the skill).
        """
        if technician.role != Role.TECHNICIAN:
            raise TechnicianUnavailableError("The selected user is not a technician.")
        cand = next((c for c in self._candidates(incident) if c.user_id == technician.id), None)
        if cand is None:
            raise TechnicianUnavailableError("The selected technician has no technician profile.")
        problems = self.policy.check(cand, self._context(incident))
        overridden = []
        for p in problems:
            if p.code in ("INACTIVE", "UNAVAILABLE"):
                raise TechnicianUnavailableError(f"{technician.full_name} cannot be assigned: {p.message.lower()}.")
            if override:
                overridden.append(p.message)
                continue
            if p.code == "AT_LIMIT":
                raise WorkloadExceededError(f"{technician.full_name} cannot be assigned: {p.message.lower()}.")
            if p.code == "NO_SKILL":
                raise MissingSkillError(f"{technician.full_name} {p.message.lower()}. "
                                        "An administrator can override this explicitly.")
        return overridden
