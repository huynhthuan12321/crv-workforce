from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_only, manager_or_director
from source.database.models import EmployeeOrm
from source.schemas.workforce import DataResponse, EmployeeOut, WorkLocationOut
from source.services.workforce import WorkLocationService

router = APIRouter()


class LocationBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=2, max_length=200)
    address: str | None = None
    latitude: float = Field(ge=8, le=24)
    longitude: float = Field(ge=102, le=110)
    radius_m: int = Field(ge=30, le=1000)
    coordinate_source: str = Field(pattern="^(device_gps|manual_coordinates)$")
    location_accuracy_m: float | None = Field(default=None, ge=0, le=10000)
    low_accuracy_confirmed: bool = False


class LocationPatchBody(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    address: str | None = None
    latitude: float | None = Field(default=None, ge=8, le=24)
    longitude: float | None = Field(default=None, ge=102, le=110)
    radius_m: int | None = Field(default=None, ge=30, le=1000)
    coordinate_source: str | None = Field(default=None, pattern="^(device_gps|manual_coordinates)$")
    location_accuracy_m: float | None = Field(default=None, ge=0, le=10000)
    low_accuracy_confirmed: bool = False


class AssignBody(BaseModel):
    location_id: int
    reason: str = Field(min_length=5, max_length=200)


@router.get("", response_model=DataResponse[list[WorkLocationOut]])
async def locations(
    active: bool | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    _: EmployeeOrm = Depends(manager_or_director),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await WorkLocationService(session).list_locations(active=active, q=q)}


@router.post("", response_model=DataResponse[WorkLocationOut])
async def create_location(body: LocationBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await WorkLocationService(session).create(
        actor, body.code, body.name, body.address, body.latitude, body.longitude, body.radius_m,
        body.coordinate_source, body.location_accuracy_m, body.low_accuracy_confirmed,
    )}


@router.patch("/{location_id}", response_model=DataResponse[WorkLocationOut])
async def update_location(location_id: int, body: LocationPatchBody, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await WorkLocationService(session).update(actor, location_id, **body.model_dump(exclude_unset=True))}


@router.post("/{location_id}/deactivate", response_model=DataResponse[WorkLocationOut])
async def deactivate(location_id: int, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await WorkLocationService(session).set_active(actor, location_id, False)}


@router.post("/{location_id}/activate", response_model=DataResponse[WorkLocationOut])
async def activate(location_id: int, actor: EmployeeOrm = Depends(manager_or_director), session: AsyncSession = Depends(get_session)):
    return {"data": await WorkLocationService(session).set_active(actor, location_id, True)}


@router.post("/employees/{employee_id}/assignment", response_model=DataResponse[EmployeeOut])
async def assign_employee(employee_id: int, body: AssignBody, actor: EmployeeOrm = Depends(manager_only), session: AsyncSession = Depends(get_session)):
    return {"data": await WorkLocationService(session).assign_employee(actor, employee_id, body.location_id, body.reason)}
