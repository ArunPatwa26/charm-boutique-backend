import random
from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.config.database import get_database


# ============================================================
# PRODUCT RECOMMENDATIONS
# ============================================================

async def get_ai_recommendations(
    user_id: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    Get AI-powered product recommendations.
    """

    db = get_database()

    recommendations = []

    # ========================================================
    # PERSONALIZED RECOMMENDATIONS
    # ========================================================

    if user_id and ObjectId.is_valid(user_id):

        user_object_id = ObjectId(user_id)

        # ----------------------------------------------------
        # Get user's paid orders
        # ----------------------------------------------------

        user_orders = await db.orders.find(
            {
                "user": user_object_id,
                "is_paid": True,
            }
        ).to_list(length=50)

        if user_orders:

            # ------------------------------------------------
            # Get purchased product IDs
            # ------------------------------------------------

            purchased_products = set()

            for order in user_orders:
                for item in order.get("items", []):

                    product_id = item.get("product")

                    if product_id:
                        purchased_products.add(
                            str(product_id)
                        )

            # ------------------------------------------------
            # Get user's wishlist
            # ------------------------------------------------

            user = await db.users.find_one(
                {
                    "_id": user_object_id
                }
            )

            wishlist_products = set()

            if user:
                wishlist_products = {
                    str(product_id)
                    for product_id in user.get(
                        "wishlist",
                        []
                    )
                }

            # ------------------------------------------------
            # Get categories of purchased products
            # ------------------------------------------------

            categories = set()

            for product_id in purchased_products:

                if not ObjectId.is_valid(product_id):
                    continue

                product = await db.products.find_one(
                    {
                        "_id": ObjectId(product_id)
                    }
                )

                if product and product.get("category"):

                    categories.add(
                        str(product["category"])
                    )

            # ------------------------------------------------
            # Find similar products
            # ------------------------------------------------

            if categories:

                valid_category_ids = []

                for category_id in categories:

                    if ObjectId.is_valid(category_id):
                        valid_category_ids.append(
                            ObjectId(category_id)
                        )

                valid_product_ids = []

                for product_id in purchased_products:

                    if ObjectId.is_valid(product_id):
                        valid_product_ids.append(
                            ObjectId(product_id)
                        )

                if valid_category_ids:

                    similar_products_cursor = (
                        db.products.find(
                            {
                                "category": {
                                    "$in": valid_category_ids
                                },
                                "_id": {
                                    "$nin": valid_product_ids
                                },
                                "is_active": True,
                                "stock": {
                                    "$gt": 0
                                },
                            }
                        )
                        .sort(
                            "average_rating",
                            -1
                        )
                        .limit(limit)
                    )

                    recommendations = await (
                        similar_products_cursor.to_list(
                            length=limit
                        )
                    )

    # ========================================================
    # FALLBACK 1 - FEATURED PRODUCTS
    # ========================================================

    if not recommendations:

        featured_products_cursor = (
            db.products.find(
                {
                    "is_active": True,
                    "is_featured": True,
                    "stock": {
                        "$gt": 0
                    },
                }
            )
            .sort(
                "average_rating",
                -1
            )
            .limit(limit)
        )

        recommendations = await (
            featured_products_cursor.to_list(
                length=limit
            )
        )

    # ========================================================
    # FALLBACK 2 - BEST SELLING PRODUCTS
    # ========================================================

    if not recommendations:

        pipeline = [
            {
                "$unwind": "$items"
            },
            {
                "$group": {
                    "_id": "$items.product",
                    "total_sold": {
                        "$sum": "$items.quantity"
                    },
                }
            },
            {
                "$sort": {
                    "total_sold": -1
                }
            },
            {
                "$limit": limit
            },
        ]

        top_selling = await (
            db.orders.aggregate(
                pipeline
            ).to_list(
                length=limit
            )
        )

        if top_selling:

            product_ids = [
                item["_id"]
                for item in top_selling
            ]

            top_products = await db.products.find(
                {
                    "_id": {
                        "$in": product_ids
                    },
                    "is_active": True,
                    "stock": {
                        "$gt": 0
                    },
                }
            ).to_list(
                length=limit
            )

            recommendations = top_products

    # ========================================================
    # FALLBACK 3 - RANDOM PRODUCTS
    # ========================================================

    if not recommendations:

        random_products = await db.products.find(
            {
                "is_active": True,
                "stock": {
                    "$gt": 0
                },
            }
        ).limit(
            limit * 2
        ).to_list(
            length=limit * 2
        )

        if random_products:

            recommendations = random.sample(
                random_products,
                min(
                    limit,
                    len(random_products)
                )
            )

    # ========================================================
    # FORMAT RECOMMENDATIONS
    # ========================================================

    formatted_recommendations = []

    for product in recommendations:

        product["id"] = str(
            product["_id"]
        )

        product.pop(
            "_id",
            None
        )

        if product.get("category") is not None:

            product["category"] = str(
                product["category"]
            )

        formatted_recommendations.append(
            product
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "success": True,
        "recommendations": formatted_recommendations,
        "count": len(
            formatted_recommendations
        ),
        "type": (
            "personalized"
            if user_id
            else "general"
        ),
    }


# ============================================================
# VIRTUAL TRY-ON
# ============================================================

async def virtual_try_on(
    product_id: str,
    user_id: Optional[str] = None,
) -> dict:
    """
    Virtual try-on feature for jewellery.
    """

    db = get_database()

    if not ObjectId.is_valid(product_id):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID",
        )

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

    return {
        "success": True,
        "message": "Virtual try-on preview ready",
        "product": {
            "id": str(
                product["_id"]
            ),
            "name": product.get(
                "name",
                "Jewellery"
            ),
            "image": product.get(
                "main_image"
            ),
        },
        "try_on_url": product.get(
            "main_image"
        ),
        "features": {
            "color_analysis": True,
            "size_recommendation": True,
            "style_suggestion": True,
        },
    }


# ============================================================
# PREDICTIVE SEARCH
# ============================================================

async def predictive_search(
    query: str,
    limit: int = 10,
) -> dict:
    """
    AI-powered predictive search.
    """

    db = get_database()

    if not query or len(query.strip()) < 2:

        return {
            "success": True,
            "suggestions": [],
            "products": [],
            "categories": [],
            "query": query,
        }

    query = query.strip()

    # ========================================================
    # PRODUCT SEARCH
    # ========================================================

    products = await db.products.find(
        {
            "$or": [
                {
                    "name": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
                {
                    "description": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
                {
                    "tags": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
                {
                    "material": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
                {
                    "gemstone": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
            ],
            "is_active": True,
            "stock": {
                "$gt": 0
            },
        }
    ).limit(
        limit
    ).to_list(
        length=limit
    )

    # ========================================================
    # CATEGORY SEARCH
    # ========================================================

    categories = await db.categories.find(
        {
            "$or": [
                {
                    "name": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
                {
                    "description": {
                        "$regex": query,
                        "$options": "i",
                    }
                },
            ],
            "is_active": True,
        }
    ).limit(
        5
    ).to_list(
        length=5
    )

    # ========================================================
    # FORMAT PRODUCTS
    # ========================================================

    formatted_products = []

    for product in products:

        product["id"] = str(
            product["_id"]
        )

        product.pop(
            "_id",
            None
        )

        if product.get("category") is not None:

            product["category"] = str(
                product["category"]
            )

        formatted_products.append(
            product
        )

    # ========================================================
    # FORMAT CATEGORIES
    # ========================================================

    formatted_categories = []

    for category in categories:

        category["id"] = str(
            category["_id"]
        )

        category.pop(
            "_id",
            None
        )

        formatted_categories.append(
            category
        )

    # ========================================================
    # SEARCH SUGGESTIONS
    # ========================================================

    suggestions = []

    # Product suggestions

    for product in formatted_products[:3]:

        suggestions.append(
            {
                "type": "product",
                "text": product.get(
                    "name",
                    ""
                ),
                "product_id": product["id"],
            }
        )

    # Category suggestions

    for category in formatted_categories:

        suggestions.append(
            {
                "type": "category",
                "text": (
                    f"Category: "
                    f"{category.get('name', '')}"
                ),
                "category_id": category["id"],
            }
        )

    # Material suggestions

    materials = set()

    for product in formatted_products:

        material = product.get(
            "material"
        )

        if material:
            materials.add(
                str(material)
            )

    for material in list(materials)[:3]:

        suggestions.append(
            {
                "type": "material",
                "text": (
                    f"Material: {material}"
                ),
            }
        )

    return {
        "success": True,
        "suggestions": suggestions,
        "products": formatted_products,
        "categories": formatted_categories,
        "query": query,
    }


# ============================================================
# TRENDING PRODUCTS
# ============================================================

async def get_trending_products(
    limit: int = 10,
) -> dict:
    """
    Get trending products based on orders.
    """

    db = get_database()

    thirty_days_ago = (
        datetime.utcnow()
        - timedelta(days=30)
    )

    pipeline = [
        {
            "$match": {
                "created_at": {
                    "$gte": thirty_days_ago
                },
                "is_paid": True,
            }
        },
        {
            "$unwind": "$items"
        },
        {
            "$group": {
                "_id": "$items.product",
                "total_sold": {
                    "$sum": "$items.quantity"
                },
                "order_count": {
                    "$sum": 1
                },
            }
        },
        {
            "$sort": {
                "total_sold": -1
            }
        },
        {
            "$limit": limit
        },
    ]

    trending = await (
        db.orders.aggregate(
            pipeline
        ).to_list(
            length=limit
        )
    )

    # ========================================================
    # PRODUCTS FROM TRENDING ORDERS
    # ========================================================

    if trending:

        product_ids = [
            item["_id"]
            for item in trending
        ]

        products = await db.products.find(
            {
                "_id": {
                    "$in": product_ids
                },
                "is_active": True,
                "stock": {
                    "$gt": 0
                },
            }
        ).to_list(
            length=limit
        )

        # Add trending metrics

        for product in products:

            for trend in trending:

                if (
                    trend["_id"]
                    == product["_id"]
                ):

                    product["trending_score"] = (
                        trend["total_sold"]
                    )

                    product["order_count"] = (
                        trend["order_count"]
                    )

                    break

        # Sort by trending score

        products.sort(
            key=lambda x: x.get(
                "trending_score",
                0
            ),
            reverse=True,
        )

        # Format products

        formatted_products = []

        for product in products:

            product["id"] = str(
                product["_id"]
            )

            product.pop(
                "_id",
                None
            )

            if product.get("category") is not None:

                product["category"] = str(
                    product["category"]
                )

            formatted_products.append(
                product
            )

        return {
            "success": True,
            "trending": formatted_products,
            "count": len(
                formatted_products
            ),
        }

    # ========================================================
    # FALLBACK - FEATURED PRODUCTS
    # ========================================================

    featured = await db.products.find(
        {
            "is_active": True,
            "is_featured": True,
            "stock": {
                "$gt": 0
            },
        }
    ).sort(
        "average_rating",
        -1
    ).limit(
        limit
    ).to_list(
        length=limit
    )

    for product in featured:

        product["id"] = str(
            product["_id"]
        )

        product.pop(
            "_id",
            None
        )

        if product.get("category") is not None:

            product["category"] = str(
                product["category"]
            )

    return {
        "success": True,
        "trending": featured,
        "count": len(featured),
    }