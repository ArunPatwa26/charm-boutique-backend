from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.config.database import get_database
from app.models.cart import CartItemAdd, CartItemUpdate


# ============================================================
# GET USER CART
# ============================================================

async def get_user_cart(
    user_id: str,
) -> dict:
    """
    Get user's cart with calculated totals.
    """

    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    # Find or create cart
    cart = await db.carts.find_one(
        {
            "user": ObjectId(user_id)
        }
    )

    if not cart:
        # Create empty cart
        now = datetime.utcnow()
        cart_dict = {
            "user": ObjectId(user_id),
            "items": [],
            "created_at": now,
            "updated_at": now,
        }

        result = await db.carts.insert_one(
            cart_dict
        )

        cart = await db.carts.find_one(
            {
                "_id": result.inserted_id
            }
        )

    # Enrich cart items with product details
    cart_items = []
    total_items = 0
    subtotal = 0.0

    for item in cart.get("items", []):
        # Get product details
        product = await db.products.find_one(
            {
                "_id": item["product"],
                "is_active": True,
            }
        )

        if product:
            # Check stock availability
            available_stock = product.get("stock", 0)
            quantity = min(
                item["quantity"],
                available_stock,
            )

            # Calculate price
            price = product.get("price", 0)
            discount_price = product.get("discount_price")
            
            item_price = discount_price if discount_price else price

            cart_items.append({
                "product_id": str(product["_id"]),
                "name": product["name"],
                "image": product["main_image"],
                "price": item_price,
                "quantity": quantity,
                "stock": available_stock,
                "total": item_price * quantity,
            })

            total_items += quantity
            subtotal += item_price * quantity

    return {
        "success": True,
        "cart": {
            "id": str(cart["_id"]),
            "user": str(cart["user"]),
            "items": cart_items,
            "total_items": total_items,
            "subtotal": round(subtotal, 2),
            "created_at": cart["created_at"],
            "updated_at": cart["updated_at"],
        },
    }


# ============================================================
# ADD ITEM TO CART
# ============================================================

async def add_to_cart(
    user_id: str,
    item_data: CartItemAdd,
) -> dict:
    """
    Add an item to the cart.
    """

    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    # Validate product
    product = await db.products.find_one(
        {
            "_id": ObjectId(item_data.product_id),
            "is_active": True,
        }
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check stock
    if product["stock"] < item_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {product['stock']} items available in stock",
        )

    # Get user's cart
    cart = await db.carts.find_one(
        {
            "user": ObjectId(user_id)
        }
    )

    if not cart:
        # Create new cart
        now = datetime.utcnow()
        cart_dict = {
            "user": ObjectId(user_id),
            "items": [],
            "created_at": now,
            "updated_at": now,
        }

        result = await db.carts.insert_one(
            cart_dict
        )

        cart = await db.carts.find_one(
            {
                "_id": result.inserted_id
            }
        )

    # Check if product already in cart
    existing_item = None
    for item in cart["items"]:
        if str(item["product"]) == item_data.product_id:
            existing_item = item
            break

    if existing_item:
        # Update quantity
        new_quantity = existing_item["quantity"] + item_data.quantity
        
        if product["stock"] < new_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {product['stock']} items available in stock",
            )

        # Calculate price
        discount_price = product.get("discount_price")
        price = discount_price if discount_price else product["price"]

        await db.carts.update_one(
            {
                "_id": cart["_id"],
                "items.product": ObjectId(item_data.product_id),
            },
            {
                "$set": {
                    "items.$.quantity": new_quantity,
                    "items.$.price": price,
                    "items.$.name": product["name"],
                    "items.$.image": product["main_image"],
                    "updated_at": datetime.utcnow(),
                }
            }
        )
    else:
        # Add new item
        discount_price = product.get("discount_price")
        price = discount_price if discount_price else product["price"]

        await db.carts.update_one(
            {
                "_id": cart["_id"]
            },
            {
                "$push": {
                    "items": {
                        "product": ObjectId(item_data.product_id),
                        "quantity": item_data.quantity,
                        "price": price,
                        "name": product["name"],
                        "image": product["main_image"],
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow(),
                }
            }
        )

    # Get updated cart
    return await get_user_cart(user_id)


# ============================================================
# UPDATE CART ITEM
# ============================================================

async def update_cart_item(
    user_id: str,
    product_id: str,
    update_data: CartItemUpdate,
) -> dict:
    """
    Update cart item quantity.
    """

    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    # Validate product
    product = await db.products.find_one(
        {
            "_id": ObjectId(product_id),
            "is_active": True,
        }
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check stock
    if product["stock"] < update_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {product['stock']} items available in stock",
        )

    # Get user's cart
    cart = await db.carts.find_one(
        {
            "user": ObjectId(user_id)
        }
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    # Check if item exists in cart
    item_exists = False
    for item in cart["items"]:
        if str(item["product"]) == product_id:
            item_exists = True
            break

    if not item_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in cart",
        )

    if update_data.quantity <= 0:
        # Remove item if quantity is 0 or negative
        await db.carts.update_one(
            {
                "_id": cart["_id"]
            },
            {
                "$pull": {
                    "items": {
                        "product": ObjectId(product_id)
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow(),
                }
            }
        )
    else:
        # Update quantity
        discount_price = product.get("discount_price")
        price = discount_price if discount_price else product["price"]

        await db.carts.update_one(
            {
                "_id": cart["_id"],
                "items.product": ObjectId(product_id),
            },
            {
                "$set": {
                    "items.$.quantity": update_data.quantity,
                    "items.$.price": price,
                    "items.$.name": product["name"],
                    "items.$.image": product["main_image"],
                    "updated_at": datetime.utcnow(),
                }
            }
        )

    # Get updated cart
    return await get_user_cart(user_id)


# ============================================================
# REMOVE ITEM FROM CART
# ============================================================

async def remove_from_cart(
    user_id: str,
    product_id: str,
) -> dict:
    """
    Remove an item from the cart.
    """

    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    # Get user's cart
    cart = await db.carts.find_one(
        {
            "user": ObjectId(user_id)
        }
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    # Check if item exists in cart
    item_exists = False
    for item in cart["items"]:
        if str(item["product"]) == product_id:
            item_exists = True
            break

    if not item_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in cart",
        )

    # Remove item
    await db.carts.update_one(
        {
            "_id": cart["_id"]
        },
        {
            "$pull": {
                "items": {
                    "product": ObjectId(product_id)
                }
            },
            "$set": {
                "updated_at": datetime.utcnow(),
            }
        }
    )

    # Get updated cart
    return await get_user_cart(user_id)


# ============================================================
# CLEAR CART
# ============================================================

async def clear_cart(
    user_id: str,
) -> dict:
    """
    Clear all items from the cart.
    """

    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    # Get user's cart
    cart = await db.carts.find_one(
        {
            "user": ObjectId(user_id)
        }
    )

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    # Clear all items
    await db.carts.update_one(
        {
            "_id": cart["_id"]
        },
        {
            "$set": {
                "items": [],
                "updated_at": datetime.utcnow(),
            }
        }
    )

    return await get_user_cart(user_id)