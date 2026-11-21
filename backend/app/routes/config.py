from fastapi import APIRouter, Depends

from app.middleware.dependencies import get_container, get_current_user, require_admin
from app.models import User
from app.schemas.config import (
    CategoryIn, CategoryOut, CategoryUpdate, ServiceIn, ServiceOut, ServiceUpdate, SettingsUpdate,
    SlaPolicyIn, SlaPolicyOut, SlaPolicyUpdate, TeamIn, TeamOut, TeamUpdate,
)
from app.services.container import Container

router = APIRouter(tags=["Administration"])


def _policy(p) -> dict:
    return {"id": p.id, "name": p.name, "priority": p.priority, "service_id": p.service_id,
            "service_name": p.service.name if p.service else None, "response_minutes": p.response_minutes,
            "resolution_minutes": p.resolution_minutes, "warning_percent": p.warning_percent,
            "is_active": p.is_active}


def _team(t) -> dict:
    return {"id": t.id, "name": t.name, "description": t.description, "lead_id": t.lead_id,
            "lead_name": t.lead.full_name if t.lead else None, "is_active": t.is_active,
            "member_count": len(t.members)}


# --------------------------------------------------------------------------- categories
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return c.repos.categories.list(only_active=user.role.value != "ADMIN")


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryIn, admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.config.create_category(admin, body.model_dump())


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryUpdate, admin: User = Depends(require_admin),
                    c: Container = Depends(get_container)):
    return c.config.update_category(admin, category_id, body.model_dump(exclude_unset=True))


# --------------------------------------------------------------------------- services
@router.get("/services", response_model=list[ServiceOut])
def list_services(user: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return c.repos.services.list(only_active=user.role.value != "ADMIN")


@router.post("/services", response_model=ServiceOut, status_code=201)
def create_service(body: ServiceIn, admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return c.config.create_service(admin, body.model_dump())


@router.patch("/services/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, body: ServiceUpdate, admin: User = Depends(require_admin),
                   c: Container = Depends(get_container)):
    return c.config.update_service(admin, service_id, body.model_dump(exclude_unset=True))


# --------------------------------------------------------------------------- SLA policies
@router.get("/sla-policies", response_model=list[SlaPolicyOut])
def list_sla_policies(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return [_policy(p) for p in c.repos.sla_policies.list()]


@router.post("/sla-policies", response_model=SlaPolicyOut, status_code=201)
def create_sla_policy(body: SlaPolicyIn, admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return _policy(c.config.create_sla_policy(admin, body.model_dump()))


@router.patch("/sla-policies/{policy_id}", response_model=SlaPolicyOut)
def update_sla_policy(policy_id: int, body: SlaPolicyUpdate, admin: User = Depends(require_admin),
                      c: Container = Depends(get_container)):
    return _policy(c.config.update_sla_policy(admin, policy_id, body.model_dump(exclude_unset=True)))


# --------------------------------------------------------------------------- teams
@router.get("/teams", response_model=list[TeamOut])
def list_teams(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return [_team(t) for t in c.repos.teams.list_all()]


@router.post("/teams", response_model=TeamOut, status_code=201)
def create_team(body: TeamIn, admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return _team(c.config.create_team(admin, body.model_dump()))


@router.patch("/teams/{team_id}", response_model=TeamOut)
def update_team(team_id: int, body: TeamUpdate, admin: User = Depends(require_admin),
                c: Container = Depends(get_container)):
    return _team(c.config.update_team(admin, team_id, body.model_dump(exclude_unset=True)))


# --------------------------------------------------------------------------- settings
@router.get("/settings")
def get_settings(admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return {"settings": c.settings.all(), **c.settings.options()}


@router.patch("/settings")
def update_settings(body: SettingsUpdate, admin: User = Depends(require_admin),
                    c: Container = Depends(get_container)):
    values = c.settings.update(admin, body.model_dump(exclude_unset=True))
    return {"settings": values, **c.settings.options()}
