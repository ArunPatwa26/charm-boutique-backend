from fastapi import APIRouter, Depends

from app.controllers.wishlist_controller import (
    get_wishlist,
    add_to_wishlist,
    remove_from_wishlist,
    clear_wishlist,
    check_in_wishlist,
)

from app.middleware.auth import (
    JWTBearer,
    get_current_user,
)

router = APIRouter()


@router.get(
    "/",
    tags=["Wishlist"],
    dependencies=[Depends(JWTBearer())],
)
async def get_user_wishlist(
    user: dict = Depends(get_current_user),
):
    """Get current user's wishlist."""
    return await get_wishlist(user["id"])


@router.post(
    "/add/{product_id}",
    tags=["Wishlist"],
    dependencies=[Depends(JWTBearer())],
)
async def add_to_user_wishlist(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """Add product to wishlist."""
    return await add_to_wishlist(user["id"], product_id)


@router.delete(
    "/remove/{product_id}",
    tags=["Wishlist"],
    dependencies=[Depends(JWTBearer())],
)
async def remove_from_user_wishlist(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove product from wishlist."""
    return await remove_from_wishlist(user["id"], product_id)


@router.delete(
    "/clear",
    tags=["Wishlist"],
    dependencies=[Depends(JWTBearer())],
)
async def clear_user_wishlist(
    user: dict = Depends(get_current_user),
):
    """Clear all items from wishlist."""
    return await clear_wishlist(user["id"])


@router.get(
    "/check/{product_id}",
    tags=["Wishlist"],
    dependencies=[Depends(JWTBearer())],
)
async def check_product_in_wishlist(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """Check if product is in wishlist."""
    return await check_in_wishlist(user["id"], product_id)