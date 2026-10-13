from bson import ObjectId
from fastapi import HTTPException, status

from app.config.database import get_database


async def get_wishlist(user_id: str) -> dict:
    """Get user's wishlist with product details."""
    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    user = await db.users.find_one(
        {"_id": ObjectId(user_id)}
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    wishlist_ids = user.get("wishlist", [])

    if not wishlist_ids:
        return {
            "success": True,
            "wishlist": [],
            "count": 0,
        }

    # Convert string IDs to ObjectIds
    product_ids = []
    for id_str in wishlist_ids:
        if ObjectId.is_valid(id_str):
            product_ids.append(ObjectId(id_str))

    if not product_ids:
        return {
            "success": True,
            "wishlist": [],
            "count": 0,
        }

    # Get product details
    products = await db.products.find(
        {
            "_id": {"$in": product_ids},
            "is_active": True,
        }
    ).to_list(length=len(product_ids))

    # Convert ObjectId to string and get category names
    for product in products:
        product["id"] = str(product["_id"])
        product.pop("_id", None)
        
        # Get category name
        if product.get("category"):
            category_obj = await db.categories.find_one(
                {"_id": product["category"]}
            )
            product["category_name"] = category_obj.get("name", "Jewellery") if category_obj else "Jewellery"
            product["category"] = str(product["category"])

    return {
        "success": True,
        "wishlist": products,
        "count": len(products),
    }


async def add_to_wishlist(user_id: str, product_id: str) -> dict:
    """Add product to user's wishlist."""
    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    # Check if product exists
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

    # Add to wishlist (using $addToSet to avoid duplicates)
    result = await db.users.update_one(
        {
            "_id": ObjectId(user_id),
        },
        {
            "$addToSet": {"wishlist": product_id}
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "success": True,
        "message": "Added to wishlist",
    }


async def remove_from_wishlist(user_id: str, product_id: str) -> dict:
    """Remove product from user's wishlist."""
    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    result = await db.users.update_one(
        {
            "_id": ObjectId(user_id),
        },
        {
            "$pull": {"wishlist": product_id}
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "success": True,
        "message": "Removed from wishlist",
    }


async def clear_wishlist(user_id: str) -> dict:
    """Clear all items from user's wishlist."""
    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    result = await db.users.update_one(
        {
            "_id": ObjectId(user_id),
        },
        {
            "$set": {"wishlist": []}
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "success": True,
        "message": "Wishlist cleared",
    }


async def check_in_wishlist(user_id: str, product_id: str) -> dict:
    """Check if product is in user's wishlist."""
    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    user = await db.users.find_one(
        {
            "_id": ObjectId(user_id),
            "wishlist": product_id,
        }
    )

    return {
        "success": True,
        "in_wishlist": user is not None,
    }