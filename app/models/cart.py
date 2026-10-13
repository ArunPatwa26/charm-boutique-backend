from datetime import datetime
from typing import Optional, List, Any
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from app.models.product import PyObjectId


class CartItem(BaseModel):
    """
    Cart item model.
    """

    product: PyObjectId = Field(
        ...,
        description="Product ID",
    )

    quantity: int = Field(
        ...,
        ge=1,
        le=99,
        description="Quantity of the product",
    )

    price: float = Field(
        ...,
        gt=0,
        description="Price at time of adding to cart",
    )

    name: str = Field(
        ...,
        description="Product name at time of adding to cart",
    )

    image: str = Field(
        ...,
        description="Product image at time of adding to cart",
    )


class Cart(BaseModel):
    """
    Cart database model.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: Optional[PyObjectId] = Field(
        default=None,
        alias="_id",
    )

    user: PyObjectId = Field(
        ...,
        description="User ID",
    )

    items: List[CartItem] = Field(
        default_factory=list,
        description="List of cart items",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


class CartItemAdd(BaseModel):
    """
    Add item to cart request.
    """

    product_id: str = Field(
        ...,
        description="Product ID",
    )

    quantity: int = Field(
        default=1,
        ge=1,
        le=99,
        description="Quantity",
    )


class CartItemUpdate(BaseModel):
    """
    Update cart item quantity request.
    """

    quantity: int = Field(
        ...,
        ge=1,
        le=99,
        description="New quantity",
    )


class CartResponse(BaseModel):
    """
    Cart response model.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: str
    user: str
    items: List[dict]
    total_items: int
    subtotal: float
    created_at: datetime
    updated_at: datetime