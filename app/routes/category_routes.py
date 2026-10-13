from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from typing import Optional

from app.controllers.category_controller import (
    create_category,
    get_categories,
    get_category_by_id,
    get_category_by_slug,
    update_category,
    delete_category,
    get_category_products,
)

from app.models.category import (
    CategoryCreate,
    CategoryUpdate,
)

from app.middleware.auth import (
    JWTBearer,
    get_current_admin,
)


router = APIRouter()


# ============================================================
# PUBLIC ROUTES
# ============================================================

@router.get(
    "/",
    tags=["Categories"],
)
async def get_all_categories(
    page: int = Query(
        1,
        ge=1,
        description="Page number",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Items per page",
    ),
    search: Optional[str] = Query(
        None,
        description="Search by category name",
    ),
):
    """
    Get all categories (public).
    """
    return await get_categories(
        page,
        limit,
        search,
        include_inactive=False,
    )


@router.get(
    "/{category_id}",
    tags=["Categories"],
)
async def get_category(
    category_id: str,
):
    """
    Get a category by ID (public).
    """
    return await get_category_by_id(
        category_id
    )


@router.get(
    "/slug/{slug}",
    tags=["Categories"],
)
async def get_category_by_slug_route(
    slug: str,
):
    """
    Get a category by slug (public).
    """
    return await get_category_by_slug(
        slug
    )


@router.get(
    "/{category_id}/products",
    tags=["Categories"],
)
async def get_category_products_route(
    category_id: str,
    page: int = Query(
        1,
        ge=1,
        description="Page number",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Items per page",
    ),
):
    """
    Get all products in a category (public).
    """
    return await get_category_products(
        category_id,
        page,
        limit,
    )


# ============================================================
# ADMIN ROUTES
# ============================================================

@router.post(
    "/",
    tags=["Categories"],
    dependencies=[Depends(JWTBearer())],
)
async def create_new_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    admin_id: str = Depends(get_current_admin),
):
    """
    Create a new category with optional image (admin only).
    """
    category_data = CategoryCreate(
        name=name,
        description=description,
    )
    
    return await create_category(
        category_data,
        image,
    )


@router.put(
    "/{category_id}",
    tags=["Categories"],
    dependencies=[Depends(JWTBearer())],
)
async def update_existing_category(
    category_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    admin_id: str = Depends(get_current_admin),
):
    """
    Update a category with optional image (admin only).
    """
    update_data = CategoryUpdate(
        name=name,
        description=description,
        is_active=is_active,
    )
    
    return await update_category(
        category_id,
        update_data,
        image,
    )


@router.delete(
    "/{category_id}",
    tags=["Categories"],
    dependencies=[Depends(JWTBearer())],
)
async def delete_existing_category(
    category_id: str,
    admin_id: str = Depends(get_current_admin),
):
    """
    Delete a category (admin only).
    """
    return await delete_category(
        category_id,
    )


@router.get(
    "/admin/all",
    tags=["Categories"],
    dependencies=[Depends(JWTBearer())],
)
async def get_all_categories_admin(
    admin_id: str = Depends(get_current_admin),
    page: int = Query(
        1,
        ge=1,
        description="Page number",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Items per page",
    ),
    search: Optional[str] = Query(
        None,
        description="Search by category name",
    ),
    include_inactive: bool = Query(
        False,
        description="Include inactive categories",
    ),
):
    """
    Get all categories (admin only).
    """
    return await get_categories(
        page,
        limit,
        search,
        include_inactive,
    )