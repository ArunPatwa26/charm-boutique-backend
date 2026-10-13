from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.controllers.ai_controller import (
    get_ai_recommendations,
    virtual_try_on,
    predictive_search,
    get_trending_products,
)

from app.middleware.auth import JWTBearer


router = APIRouter()


# ============================================================
# RECOMMENDATIONS
# ============================================================

@router.get(
    "/recommendations",
    tags=["AI Features"],
)
async def get_recommendations(
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of recommendations",
    ),
    token: Optional[str] = Depends(
        JWTBearer(auto_error=False)
    ),
):
    """
    Get AI-powered product recommendations.
    """

    user_id = None

    if token:

        from app.controllers.auth_controller import (
            get_current_user
        )

        try:

            user = await get_current_user(
                token
            )

            user_id = user.get(
                "id"
            )

        except Exception:
            user_id = None

    return await get_ai_recommendations(
        user_id=user_id,
        limit=limit,
    )


# ============================================================
# VIRTUAL TRY-ON
# ============================================================

@router.get(
    "/try-on/{product_id}",
    tags=["AI Features"],
)
async def try_on_product(
    product_id: str,
):
    """
    Virtual try-on for jewellery products.
    """

    return await virtual_try_on(
        product_id=product_id
    )


# ============================================================
# PREDICTIVE SEARCH
# ============================================================

@router.get(
    "/search/predict",
    tags=["AI Features"],
)
async def search_predict(
    query: str = Query(
        ...,
        min_length=2,
        description="Search query",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=20,
        description="Number of results",
    ),
):
    """
    AI-powered predictive search.
    """

    return await predictive_search(
        query=query,
        limit=limit,
    )


# ============================================================
# TRENDING PRODUCTS
# ============================================================

@router.get(
    "/trending",
    tags=["AI Features"],
)
async def get_trending(
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of trending products",
    ),
):
    """
    Get trending products based on popularity.
    """

    return await get_trending_products(
        limit=limit
    )