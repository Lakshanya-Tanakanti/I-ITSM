from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domain.enums import Role
from app.middleware.dependencies import (
    get_container, get_current_user, require_admin, require_roles, require_technician,
)
from app.models import User
from app.schemas.user import (
    AvailabilityUpdate, TechnicianProfileUpdate, UserCreate, UserOut, UserUpdate,
)
from app.services.container import Container
from app.services.presenter import user_full

router = APIRouter(tags=["Users and technicians"])


@router.get("/users", response_model=list[UserOut])
def list_users(role: Optional[Role] = None, q: Optional[str] = Query(default=None, max_length=100),
               is_active: Optional[bool] = None, admin: User = Depends(require_admin),
               c: Container = Depends(get_container)):
    return [user_full(u) for u in c.users.list(admin, role, q, is_active)]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return user_full(c.users.create(admin, body.model_dump()))


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, actor: User = Depends(get_current_user), c: Container = Depends(get_container)):
    return user_full(c.users.get_for_actor(actor, user_id))


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, actor: User = Depends(get_current_user),
                c: Container = Depends(get_container)):
    return user_full(c.users.update(actor, user_id, body.model_dump(exclude_unset=True)))


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, admin: User = Depends(require_admin), c: Container = Depends(get_container)):
    return user_full(c.users.deactivate(admin, user_id))


@router.put("/users/{user_id}/technician-profile", response_model=UserOut)
def update_profile(user_id: int, body: TechnicianProfileUpdate, admin: User = Depends(require_admin),
                   c: Container = Depends(get_container)):
    return user_full(c.users.update_technician_profile(admin, user_id, body.model_dump(exclude_unset=True)))


@router.get("/technicians/workload")
def technician_workload(actor: User = Depends(require_roles(Role.ADMIN, Role.TECHNICIAN)),
                        c: Container = Depends(get_container)):
    return c.users.workload(actor)


@router.patch("/technicians/me/availability", response_model=UserOut)
def set_availability(body: AvailabilityUpdate, tech: User = Depends(require_technician),
                     c: Container = Depends(get_container)):
    return user_full(c.users.set_availability(tech, body.is_available))


@router.get("/technicians/me/queue")
def my_queue(tech: User = Depends(require_technician), c: Container = Depends(get_container)):
    from app.repositories import IncidentFilters
    from app.services.incident_service import parse_status_filter
    filters = IncidentFilters(statuses=parse_status_filter("OPEN"), page=1, page_size=100, sort="-priority")
    items, total = c.incidents.list_incidents(tech, filters)
    return {"items": c.presenter.list_items(items), "total": total}
