from fastapi import HTTPException
from openapi_server.models.error_response import ErrorResponse

from typing import Dict, List  
import importlib
import pkgutil

from fastapi import (
    APIRouter,
    Body,
    Path,
    Query,
    Response,
    status as http_status,
    HTTPException,
)

from openapi_server.models.product_create import ProductCreate
from openapi_server.models.product_page_response import ProductPageResponse
from openapi_server.models.product_response import ProductResponse
from openapi_server.models.product_update import ProductUpdate


from src.db import SessionLocal
from src.service import ProductService

router = APIRouter()


def raise_contract_error(status_code: int, error_code: str, message: str, details: dict | None = None) -> None:
    err = ErrorResponse.from_dict(
        {"error_code": error_code, "message": message, "details": details}
    )

    raise HTTPException(status_code=status_code, detail=err.to_dict())


@router.delete(
    "/products/{id}",
    responses={
        204: {"description": "Archived (status set to ARCHIVED)"},
        404: {"description": "Not found"},
    },
    tags=["Products"],
    summary="Soft delete product (set status ARCHIVED)",
    response_model_by_alias=True,
)
async def archive_product(
    id: str = Path(..., description=""),
    response: Response = None,
) -> None:
    with SessionLocal() as db:
        ok = ProductService(db).archive(id)

    if not ok:
        raise_contract_error(
            status_code=http_status.HTTP_404_NOT_FOUND,
            error_code="PRODUCT_NOT_FOUND",
            message="Product not found",
            details={"id": id},
        )

    response.status_code = http_status.HTTP_204_NO_CONTENT
    return None


@router.post(
    "/products",
    responses={
        201: {"model": ProductResponse, "description": "Created"},
        400: {"description": "Validation error"},
    },
    tags=["Products"],
    summary="Create product",
    response_model_by_alias=True,
)
async def create_product(
    product_create: ProductCreate = Body(None, description=""),
    response: Response = None,
) -> ProductResponse:
    if product_create is None:
        raise_contract_error(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            message="Request body is required",
            details=None,
        )

    with SessionLocal() as db:
        created = ProductService(db).create(product_create)

    response.status_code = http_status.HTTP_201_CREATED
    return created

@router.get("/products/{id}", response_model_by_alias=True, tags=["Products"])
async def get_product_by_id(id: str = Path(..., description="")) -> ProductResponse:
    with SessionLocal() as db:
        product = ProductService(db).get(id)

    if product is None:
        raise_contract_error(404, "PRODUCT_NOT_FOUND", "Product not found", {"id": id})

    return product


@router.get(
    "/products",
    responses={
        200: {"model": ProductPageResponse, "description": "Page of products"},
    },
    tags=["Products"],
    summary="List products with pagination and filtering",
    response_model_by_alias=True,
)
async def list_products(
    page: int = Query(0, description="Page number (starts from 0)", alias="page", ge=0),
    size: int = Query(20, description="Page size", alias="size", ge=1),
    status: str = Query(None, description="Filter by status", alias="status"),
    category: str = Query(None, description="Filter by category (exact match)", alias="category", min_length=1),
) -> ProductPageResponse:
    with SessionLocal() as db:
        return ProductService(db).list(page, size, status, category)


@router.put(
    "/products/{id}",
    responses={
        200: {"model": ProductResponse, "description": "Updated"},
        400: {"description": "Validation error"},
        404: {"description": "Not found"},
    },
    tags=["Products"],
    summary="Update product",
    response_model_by_alias=True,
)
async def update_product(
    id: str = Path(..., description=""),
    product_update: ProductUpdate = Body(None, description=""),
) -> ProductResponse:
    if product_update is None:
        raise_contract_error(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            message="Request body is required",
            details=None,
        )

    with SessionLocal() as db:
        updated = ProductService(db).update(id, product_update)

    if updated is None:
        raise_contract_error(
            status_code=http_status.HTTP_404_NOT_FOUND,
            error_code="PRODUCT_NOT_FOUND",
            message="Product not found",
            details={"id": id},
        )

    return updated