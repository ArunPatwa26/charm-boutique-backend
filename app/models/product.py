from datetime import datetime
from typing import Optional, List, Any

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict

from app.models.user import PyObjectId
from app.models.category import PyObjectId


# ============================================================
# PRODUCT DIMENSIONS
# ============================================================

class Dimensions(BaseModel):
    """
    Product dimensions.
    """

    height: Optional[float] = None
    width: Optional[float] = None
    depth: Optional[float] = None


# ============================================================
# PRODUCT REVIEW
# ============================================================

class Review(BaseModel):
    """
    Product review model.
    """

    user: PyObjectId

    rating: float = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 to 5",
    )

    comment: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Review comment",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


# ============================================================
# PRODUCT DATABASE MODEL
# ============================================================

class Product(BaseModel):
    """
    Product database model.
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

    name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Product name",
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Product description",
    )

    price: float = Field(
        ...,
        gt=0,
        description="Product price",
    )

    discount_price: Optional[float] = Field(
        default=None,
        gt=0,
        description="Discounted price",
    )

    category: PyObjectId = Field(
        ...,
        description="Category ID",
    )

    images: List[str] = Field(
        default_factory=list,
        description="Product images",
    )

    main_image: Optional[str] = Field(
        default=None,
        description="Main product image",
    )

    material: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Product material",
    )

    gemstone: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Product gemstone",
    )

    weight: Optional[float] = Field(
        default=None,
        ge=0,
        description="Product weight",
    )

    dimensions: Optional[Dimensions] = Field(
        default=None,
        description="Product dimensions",
    )

    stock: int = Field(
        default=0,
        ge=0,
        description="Available stock",
    )

    is_featured: bool = Field(
        default=False,
    )

    is_ai_recommended: bool = Field(
        default=False,
    )

    tags: List[str] = Field(
        default_factory=list,
    )

    average_rating: float = Field(
        default=0,
        ge=0,
        le=5,
    )

    num_reviews: int = Field(
        default=0,
        ge=0,
    )

    reviews: List[Review] = Field(
        default_factory=list,
    )

    is_active: bool = Field(
        default=True,
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


# ============================================================
# CREATE PRODUCT MODEL
# ============================================================

class ProductCreate(BaseModel):
    """
    Product creation request model.
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=200,
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )

    price: float = Field(
        ...,
        gt=0,
    )

    discount_price: Optional[float] = Field(
        default=None,
        gt=0,
    )

    category: str = Field(
        ...,
        description="Category MongoDB ObjectId",
    )

    material: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    gemstone: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    weight: Optional[float] = Field(
        default=None,
        ge=0,
    )

    dimensions: Optional[dict] = Field(
        default=None,
    )

    stock: int = Field(
        ...,
        ge=0,
    )

    is_featured: bool = Field(
        default=False,
    )

    is_ai_recommended: bool = Field(
        default=False,
    )

    tags: List[str] = Field(
        default_factory=list,
    )


# ============================================================
# UPDATE PRODUCT MODEL
# ============================================================

class ProductUpdate(BaseModel):
    """
    Product update request model.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    description: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=2000,
    )

    price: Optional[float] = Field(
        default=None,
        gt=0,
    )

    discount_price: Optional[float] = Field(
        default=None,
        gt=0,
    )

    category: Optional[str] = Field(
        default=None,
    )

    material: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    gemstone: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    weight: Optional[float] = Field(
        default=None,
        ge=0,
    )

    dimensions: Optional[dict] = Field(
        default=None,
    )

    stock: Optional[int] = Field(
        default=None,
        ge=0,
    )

    is_featured: Optional[bool] = None

    is_ai_recommended: Optional[bool] = None

    tags: Optional[List[str]] = None

    is_active: Optional[bool] = None


# ============================================================
# PRODUCT RESPONSE MODEL
# ============================================================

class ProductResponse(BaseModel):
    """
    Product response model.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: str

    name: str

    description: str

    price: float

    discount_price: Optional[float] = None

    category: str

    images: List[str] = Field(
        default_factory=list,
    )

    main_image: Optional[str] = None

    material: str

    gemstone: Optional[str] = None

    weight: Optional[float] = None

    dimensions: Optional[dict] = None

    stock: int

    is_featured: bool

    is_ai_recommended: bool

    tags: List[str] = Field(
        default_factory=list,
    )

    average_rating: float = 0

    num_reviews: int = 0

    is_active: bool

    created_at: datetime

    updated_at: datetime