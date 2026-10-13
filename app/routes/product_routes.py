from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from typing import Optional, List

from app.controllers.product_controller import (
    create_product,
    get_products,
    get_product_by_id,
    update_product,
    delete_product,
    admin_get_all_products,
)

from app.models.product import (
    ProductCreate,
    ProductUpdate,
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
    tags=["Products"],
)
async def get_all_products(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    material: Optional[str] = Query(None),
    gemstone: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    is_ai_recommended: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Get all products with filters and pagination (public).
    """
    return await get_products(
        page,
        limit,
        category,
        min_price,
        max_price,
        material,
        gemstone,
        sort_by,
        is_featured,
        is_ai_recommended,
        search,
    )


@router.get(
    "/{product_id}",
    tags=["Products"],
)
async def get_product(
    product_id: str,
):
    """
    Get a product by ID (public).
    """
    return await get_product_by_id(
        product_id
    )


# ============================================================
# ADMIN ROUTES
# ============================================================

@router.get(
    "/admin/all",
    tags=["Products"],
    dependencies=[Depends(JWTBearer())],
)
async def admin_get_all_products_route(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    admin_id: str = Depends(get_current_admin),
):
    """
    Get all products for admin (includes inactive products).
    """
    return await admin_get_all_products(
        page,
        limit,
        search,
        category,
        status,
    )


@router.post(
    "/",
    tags=["Products"],
    dependencies=[Depends(JWTBearer())],
)
async def create_new_product(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    material: str = Form(...),
    stock: int = Form(...),
    discount_price: Optional[float] = Form(None),
    gemstone: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    dimensions: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    is_ai_recommended: bool = Form(False),
    tags: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    admin_id: str = Depends(get_current_admin),
):
    """
    Create a new product with images (admin only).
    """
    # Parse tags
    tags_list = tags.split(",") if tags else []
    
    # Parse dimensions
    dimensions_dict = None
    if dimensions:
        try:
            import json
            dimensions_dict = json.loads(dimensions)
        except:
            pass
    
    product_data = ProductCreate(
        name=name,
        description=description,
        price=price,
        discount_price=discount_price,
        category=category,
        material=material,
        gemstone=gemstone,
        weight=weight,
        dimensions=dimensions_dict,
        stock=stock,
        is_featured=is_featured,
        is_ai_recommended=is_ai_recommended,
        tags=tags_list,
    )
    
    return await create_product(
        product_data,
        images,
    )


@router.put(
    "/{product_id}",
    tags=["Products"],
    dependencies=[Depends(JWTBearer())],
)
async def update_existing_product(
    product_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    category: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    stock: Optional[int] = Form(None),
    discount_price: Optional[float] = Form(None),
    gemstone: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    dimensions: Optional[str] = Form(None),
    is_featured: Optional[bool] = Form(None),
    is_ai_recommended: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    tags: Optional[str] = Form(None),
    new_images: List[UploadFile] = File(default=[]),
    remove_images: Optional[str] = Form(None),
    admin_id: str = Depends(get_current_admin),
):
    """
    Update a product (admin only).
    """
    # Parse tags
    tags_list = tags.split(",") if tags else None
    
    # Parse remove_images
    remove_images_list = remove_images.split(",") if remove_images else None
    
    # Parse dimensions
    dimensions_dict = None
    if dimensions:
        try:
            import json
            dimensions_dict = json.loads(dimensions)
        except:
            pass
    
    update_data = ProductUpdate(
        name=name,
        description=description,
        price=price,
        discount_price=discount_price,
        category=category,
        material=material,
        gemstone=gemstone,
        weight=weight,
        dimensions=dimensions_dict,
        stock=stock,
        is_featured=is_featured,
        is_ai_recommended=is_ai_recommended,
        tags=tags_list,
        is_active=is_active,
    )
    
    return await update_product(
        product_id,
        update_data,
        new_images,
        remove_images_list,
    )


@router.delete(
    "/{product_id}",
    tags=["Products"],
    dependencies=[Depends(JWTBearer())],
)
async def delete_existing_product(
    product_id: str,
    admin_id: str = Depends(get_current_admin),
):
    """
    Delete a product (admin only).
    """
    return await delete_product(
        product_id,
    )