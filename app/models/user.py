from datetime import datetime
from typing import Optional, List, Any

from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    """
    Custom MongoDB ObjectId type compatible with Pydantic v2.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any,
    ) -> core_schema.CoreSchema:

        return core_schema.no_info_plain_validator_function(
            cls.validate
        )

    @classmethod
    def validate(cls, value: Any) -> ObjectId:
        """
        Validate and convert a value into MongoDB ObjectId.
        """

        if isinstance(value, ObjectId):
            return value

        if isinstance(value, str) and ObjectId.is_valid(value):
            return ObjectId(value)

        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: core_schema.CoreSchema,
        handler: Any,
    ) -> dict:

        return {
            "type": "string",
            "format": "objectid",
        }


class Address(BaseModel):
    """
    User address model.
    """

    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None


class User(BaseModel):
    """
    User database model.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "password123",
                "role": "user",
            }
        },
    )

    id: Optional[PyObjectId] = Field(
        default=None,
        alias="_id",
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
    )

    email: EmailStr = Field(
        ...,
        description="User's email address",
    )

    password: str = Field(
        ...,
        min_length=6,
        description="User's password (hashed)",
    )

    role: str = Field(
        default="user",
        description="User role: user or admin",
    )

    avatar: str = Field(
        default="https://via.placeholder.com/150",
        description="Profile picture URL",
    )

    phone: Optional[str] = Field(
        default=None,
        description="Phone number",
    )

    address: Optional[Address] = None

    wishlist: List[str] = Field(
        default_factory=list,
        description="List of product IDs",
    )

    is_active: bool = Field(
        default=True,
        description="Is user active",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


class UserCreate(BaseModel):
    """
    User registration request.
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=6,
    )


class UserLogin(BaseModel):
    """
    User login request.
    """

    email: EmailStr

    password: str

class UserUpdate(BaseModel):
    """
    User profile update request.
    All fields are optional because the user may update
    only part of their profile.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="User's full name",
    )

    phone: Optional[str] = Field(
        default=None,
        description="Phone number",
    )

    address: Optional[Address] = Field(
        default=None,
        description="User address",
    )

    avatar: Optional[str] = Field(
        default=None,
        description="Profile picture URL",
    )    


class UserResponse(BaseModel):
    """
    User response model.
    Password is intentionally excluded.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: str
    name: str
    email: str
    role: str
    avatar: str
    phone: Optional[str] = None
    address: Optional[Address] = None
    wishlist: List[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime