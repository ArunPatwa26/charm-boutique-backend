from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict

from app.models.user import PyObjectId


# ============================================================
# CATEGORY DATABASE MODEL
# ============================================================

class Category(BaseModel):
    """
    Category database model.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "Necklaces",
                "slug": "necklaces",
                "description": "Beautiful necklaces for every occasion",
                "image": "https://via.placeholder.com/300",
            }
        },
    )

    # MongoDB ID
    id: Optional[PyObjectId] = Field(
        default=None,
        alias="_id",
    )

    # Category name
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Category name",
    )

    # URL-friendly category name
    slug: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="URL-friendly version of the category name",
    )

    # Category description
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Category description",
    )

    # Category image
    image: str = Field(
        default="https://via.placeholder.com/300",
        description="Category image URL",
    )

    # Category status
    is_active: bool = Field(
        default=True,
        description="Is category active",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


# ============================================================
# CATEGORY CREATE MODEL
# ============================================================

class CategoryCreate(BaseModel):
    """
    Category creation request model.
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    image: Optional[str] = Field(
        default=None,
    )


# ============================================================
# CATEGORY UPDATE MODEL
# ============================================================

class CategoryUpdate(BaseModel):
    """
    Category update request model.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    image: Optional[str] = None

    is_active: Optional[bool] = None


# ============================================================
# CATEGORY RESPONSE MODEL
# ============================================================

class CategoryResponse(BaseModel):
    """
    Category response model.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: str

    name: str

    slug: str

    description: Optional[str] = None

    image: str

    is_active: bool

    created_at: datetime

    updated_at: datetime