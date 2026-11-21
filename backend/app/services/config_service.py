"""Administrator configuration: categories, services, SLA policies and teams."""
from app.domain.enums import EventType, Priority
from app.domain.exceptions import (
    DuplicateResourceError, InvalidInputError, NotFoundError,
)
from app.models import IncidentCategory, Service, SlaPolicy, SupportTeam
from app.services.base import BaseService, transactional


def _clean_keywords(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    seen, out = set(), []
    for k in items:
        k = k.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return ", ".join(out) or None


class ConfigService(BaseService):
    # ------------------------------------------------------------------ categories
    @transactional
    def create_category(self, actor, data: dict) -> IncidentCategory:
        if self.repos.categories.get_by_name(data["name"]):
            raise DuplicateResourceError("A category with this name already exists.")
        cat = IncidentCategory(name=data["name"].strip(), description=data.get("description"),
                               keywords=_clean_keywords(data.get("keywords")), is_active=True)
        self.repos.categories.add(cat)
        self.emit(EventType.CONFIG_CHANGED, f"{actor.full_name} created category '{cat.name}'", actor=actor,
                  entity="category", id=cat.id)
        return cat

    @transactional
    def update_category(self, actor, category_id: int, changes: dict) -> IncidentCategory:
        cat = self.repos.categories.get(category_id)
        if cat is None:
            raise NotFoundError("Category not found.")
        if changes.get("name") and changes["name"].strip().lower() != cat.name.lower():
            if self.repos.categories.get_by_name(changes["name"]):
                raise DuplicateResourceError("A category with this name already exists.")
            cat.name = changes["name"].strip()
        if "description" in changes:
            cat.description = changes["description"]
        if "keywords" in changes:
            cat.keywords = _clean_keywords(changes["keywords"])
        if changes.get("is_active") is not None:
            cat.is_active = changes["is_active"]
        self.emit(EventType.CONFIG_CHANGED, f"{actor.full_name} updated category '{cat.name}'", actor=actor,
                  entity="category", id=cat.id)
        return cat

    # ------------------------------------------------------------------ services
    @transactional
    def create_service(self, actor, data: dict) -> Service:
        if self.repos.services.get_by_name(data["name"]):
            raise DuplicateResourceError("A service with this name already exists.")
        svc = Service(name=data["name"].strip(), description=data.get("description"),
                      business_criticality=data["business_criticality"], is_active=True)
        self.repos.services.add(svc)
        self.emit(EventType.CONFIG_CHANGED,
                  f"{actor.full_name} created service '{svc.name}' (criticality {svc.business_criticality})",
                  actor=actor, entity="service", id=svc.id)
        return svc

    @transactional
    def update_service(self, actor, service_id: int, changes: dict) -> Service:
        svc = self.repos.services.get(service_id)
        if svc is None:
            raise NotFoundError("Service not found.")
        if changes.get("name") and changes["name"].strip().lower() != svc.name.lower():
            if self.repos.services.get_by_name(changes["name"]):
                raise DuplicateResourceError("A service with this name already exists.")
            svc.name = changes["name"].strip()
        if "description" in changes:
            svc.description = changes["description"]
        if changes.get("business_criticality") is not None:
            svc.business_criticality = changes["business_criticality"]
        if changes.get("is_active") is not None:
            svc.is_active = changes["is_active"]
        self.emit(EventType.CONFIG_CHANGED, f"{actor.full_name} updated service '{svc.name}'", actor=actor,
                  entity="service", id=svc.id)
        return svc

    # ------------------------------------------------------------------ SLA policies
    @staticmethod
    def _check_policy(response, resolution, warning) -> None:
        if response <= 0 or resolution <= 0:
            raise InvalidInputError("SLA targets must be greater than zero.")
        if resolution < response:
            raise InvalidInputError("The resolution target cannot be shorter than the response target.")
        if not 1 <= warning <= 99:
            raise InvalidInputError("The warning percentage must be between 1 and 99.")

    @transactional
    def create_sla_policy(self, actor, data: dict) -> SlaPolicy:
        self._check_policy(data["response_minutes"], data["resolution_minutes"], data.get("warning_percent", 75))
        if data.get("service_id") and self.repos.services.get(data["service_id"]) is None:
            raise InvalidInputError("The selected service does not exist.")
        policy = SlaPolicy(
            name=data["name"].strip(), priority=Priority(data["priority"]), service_id=data.get("service_id"),
            response_minutes=data["response_minutes"], resolution_minutes=data["resolution_minutes"],
            warning_percent=data.get("warning_percent", 75), is_active=True)
        self.repos.sla_policies.add(policy)
        self.emit(EventType.CONFIG_CHANGED, f"{actor.full_name} created SLA policy '{policy.name}'", actor=actor,
                  entity="sla_policy", id=policy.id)
        return policy

    @transactional
    def update_sla_policy(self, actor, policy_id: int, changes: dict) -> SlaPolicy:
        policy = self.repos.sla_policies.get(policy_id)
        if policy is None:
            raise NotFoundError("SLA policy not found.")
        response = changes.get("response_minutes", policy.response_minutes)
        resolution = changes.get("resolution_minutes", policy.resolution_minutes)
        warning = changes.get("warning_percent", policy.warning_percent)
        self._check_policy(response, resolution, warning)
        if changes.get("name"):
            policy.name = changes["name"].strip()
        policy.response_minutes, policy.resolution_minutes, policy.warning_percent = response, resolution, warning
        if "service_id" in changes:
            if changes["service_id"] and self.repos.services.get(changes["service_id"]) is None:
                raise InvalidInputError("The selected service does not exist.")
            policy.service_id = changes["service_id"]
        if changes.get("priority"):
            policy.priority = Priority(changes["priority"])
        if changes.get("is_active") is not None:
            policy.is_active = changes["is_active"]
        self.emit(EventType.CONFIG_CHANGED,
                  f"{actor.full_name} updated SLA policy '{policy.name}' "
                  f"({policy.response_minutes}/{policy.resolution_minutes} min)",
                  actor=actor, entity="sla_policy", id=policy.id)
        return policy

    # ------------------------------------------------------------------ teams
    @transactional
    def create_team(self, actor, data: dict) -> SupportTeam:
        if self.repos.teams.get_by_name(data["name"]):
            raise DuplicateResourceError("A team with this name already exists.")
        team = SupportTeam(name=data["name"].strip(), description=data.get("description"), is_active=True)
        self._set_lead(team, data.get("lead_id"))
        self.repos.teams.add(team)
        self.emit(EventType.CONFIG_CHANGED, f"{actor.full_name} created team '{team.name}'", actor=actor,
                  entity="team", id=team.id)
        return team

    @transactional
    def update_team(self, actor, team_id: int, changes: dict) -> SupportTeam:
        team = self.repos.teams.get(team_id)
        if team is None:
            raise NotFoundError("Team not found.")
        if changes.get("name") and changes["name"].strip().lower() != team.name.lower():
            if self.repos.teams.get_by_name(changes["name"]):
                raise DuplicateResourceError("A team with this name already exists.")
            team.name = changes["name"].strip()
        if "description" in changes:
            team.description = changes["description"]
        if "lead_id" in changes:
            self._set_lead(team, changes["lead_id"])
        if changes.get("is_active") is not None:
            team.is_active = changes["is_active"]
        self.emit(EventType.CONFIG_CHANGED, f"{actor.full_name} updated team '{team.name}'", actor=actor,
                  entity="team", id=team.id)
        return team

    def _set_lead(self, team: SupportTeam, lead_id) -> None:
        if not lead_id:
            team.lead, team.lead_id = None, None
            return
        lead = self.repos.users.get(lead_id)
        if lead is None or lead.role.value != "TECHNICIAN":
            raise InvalidInputError("The team lead must be an existing technician.")
        team.lead, team.lead_id = lead, lead.id
