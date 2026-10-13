from fastapi import APIRouter, Depends, HTTPException

from app.controllers.cart_controller import (
    get_user_cart,
    add_to_cart,
    update_cart_item,
    remove_from_cart,
    clear_cart,
)

from app.models.cart import (
    CartItemAdd,
    CartItemUpdate,
)

from app.middleware.auth import (
    JWTBearer,
    get_current_user,
)


router = APIRouter()


# ============================================================
# GET CART
# ============================================================

@router.get(
    "/",
    tags=["Cart"],
    dependencies=[Depends(JWTBearer())],
)
async def get_cart(
    user: dict = Depends(get_current_user),
):
    """
    Get current user's cart.
    """
    return await get_user_cart(
        user["id"]
    )


# ============================================================
# ADD TO CART
# ============================================================

@router.post(
    "/add",
    tags=["Cart"],
    dependencies=[Depends(JWTBearer())],
)
async def add_item_to_cart(
    item_data: CartItemAdd,
    user: dict = Depends(get_current_user),
):
    """
    Add an item to the cart.
    """
    return await add_to_cart(
        user["id"],
        item_data,
    )


# ============================================================
# UPDATE CART ITEM
# ============================================================

@router.put(
    "/update/{product_id}",
    tags=["Cart"],
    dependencies=[Depends(JWTBearer())],
)
async def update_item(
    product_id: str,
    update_data: CartItemUpdate,
    user: dict = Depends(get_current_user),
):
    """
    Update cart item quantity.
    """
    return await update_cart_item(
        user["id"],
        product_id,
        update_data,
    )


# ============================================================
# REMOVE FROM CART
# ============================================================

@router.delete(
    "/remove/{product_id}",
    tags=["Cart"],
    dependencies=[Depends(JWTBearer())],
)
async def remove_item(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Remove an item from the cart.
    """
    return await remove_from_cart(
        user["id"],
        product_id,
    )


# ============================================================
# CLEAR CART
# ============================================================

@router.delete(
    "/clear",
    tags=["Cart"],
    dependencies=[Depends(JWTBearer())],
)
async def clear_cart_items(
    user: dict = Depends(get_current_user),
):
    """
    Clear all items from the cart.
    """
    return await clear_cart(
        user["id"],
    )