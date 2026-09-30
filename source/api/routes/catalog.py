from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from source.api.dependencies import get_session
from source.api.workforce_auth import manager_or_director
from source.database.models import EmployeeOrm
from source.schemas.workforce import CatalogEmployeeOptionOut, CatalogProductOut, DataResponse
from source.services.workforce import ProductCatalogService

router = APIRouter()


class ProductBody(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    kg_per_unit: Decimal = Field(gt=0)
    unit_code: str = Field(default="BAG", min_length=1, max_length=16)
    unit_label: str = Field(default="Túi", min_length=1, max_length=32)
    sort_order: int | None = None
    scope: str = Field(default="all", pattern="^(all|restricted)$")
    location_ids: list[int] = []
    employee_ids: list[int] = []


class ProductPatchBody(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    kg_per_unit: Decimal | None = Field(default=None, gt=0)
    unit_code: str | None = Field(default=None, min_length=1, max_length=16)
    unit_label: str | None = Field(default=None, min_length=1, max_length=32)
    sort_order: int | None = None


class ProductScopeBody(BaseModel):
    scope: str = Field(pattern="^(all|restricted)$")
    location_ids: list[int] = []
    employee_ids: list[int] = []


class ProductReorderBody(BaseModel):
    items: list[dict]


@router.get("/products", response_model=DataResponse[list[CatalogProductOut]])
async def products(
    include_deleted: bool = False,
    q: str | None = Query(default=None, min_length=1, max_length=100),
    _: EmployeeOrm = Depends(manager_or_director),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await ProductCatalogService(session).list_products(include_deleted=include_deleted, q=q)}


@router.post("/products", response_model=DataResponse[CatalogProductOut])
async def create_product(body: ProductBody, actor: EmployeeOrm = Depends(manager_or_director),
                         session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).create_product(
        actor, body.code, body.name, body.kg_per_unit, body.unit_code, body.unit_label,
        body.sort_order, body.scope, body.location_ids, body.employee_ids,
    )}


@router.get("/products/{product_id}", response_model=DataResponse[CatalogProductOut])
async def product(product_id: int, _: EmployeeOrm = Depends(manager_or_director),
                  session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).get_product(product_id)}


@router.patch("/products/{product_id}", response_model=DataResponse[CatalogProductOut])
async def update_product(product_id: int, body: ProductPatchBody, actor: EmployeeOrm = Depends(manager_or_director),
                         session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).update_product(
        actor, product_id, **body.model_dump(exclude_unset=True),
    )}


@router.post("/products/{product_id}/deactivate", response_model=DataResponse[CatalogProductOut])
async def deactivate_product(product_id: int, actor: EmployeeOrm = Depends(manager_or_director),
                             session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).set_active(actor, product_id, False)}


@router.post("/products/{product_id}/reactivate", response_model=DataResponse[CatalogProductOut])
async def reactivate_product(product_id: int, actor: EmployeeOrm = Depends(manager_or_director),
                             session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).set_active(actor, product_id, True)}


@router.delete("/products/{product_id}", response_model=DataResponse[CatalogProductOut])
async def delete_product(product_id: int, actor: EmployeeOrm = Depends(manager_or_director),
                         session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).delete_product(actor, product_id)}


@router.patch("/products/{product_id}/scope", response_model=DataResponse[CatalogProductOut])
async def update_scope(product_id: int, body: ProductScopeBody, actor: EmployeeOrm = Depends(manager_or_director),
                       session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).update_scope(
        actor, product_id, body.scope, body.location_ids, body.employee_ids,
    )}


@router.post("/products/reorder", response_model=DataResponse[list[CatalogProductOut]])
async def reorder_products(body: ProductReorderBody, actor: EmployeeOrm = Depends(manager_or_director),
                           session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).reorder(actor, body.items)}


@router.get("/employee-options", response_model=DataResponse[list[CatalogEmployeeOptionOut]])
async def employee_options(_: EmployeeOrm = Depends(manager_or_director),
                           session: AsyncSession = Depends(get_session)):
    return {"data": await ProductCatalogService(session).employee_options()}
