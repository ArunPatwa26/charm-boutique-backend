from datetime import datetime
from typing import Optional, Any
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema


# ============================================================
# PyObjectId — Pydantic v2 compatible
# ============================================================
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, value: Any) -> ObjectId:
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
        return {"type": "string", "format": "objectid"}


# ============================================================
# PAYMENT PROOF MODEL
# ============================================================
class PaymentProof(BaseModel):
    """
    Manual UPI payment proof uploaded by customer.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "order": "64a1b2c3d4e5f6a7b8c9d0e1",
                "user": "64a1b2c3d4e5f6a7b8c9d0e2",
                "screenshot_url": "https://res.cloudinary.com/.../proof.jpg",
                "screenshot_public_id": "ai-jewellery-shop/payment-proofs/proof_id",
                "customer_note": "Paid via PhonePe at 3:45 PM",
                "status": "verification_pending",
            }
        },
    )

    id: Optional[PyObjectId] = Field(
        default=None,
        alias="_id",
    )

    order: PyObjectId = Field(
        ...,
        description="Reference to the order",
    )

    user: PyObjectId = Field(
        ...,
        description="User who uploaded the proof",
    )

    screenshot_url: str = Field(
        ...,
        description="Cloudinary secure URL of the screenshot",
    )

    screenshot_public_id: str = Field(
        ...,
        description="Cloudinary public_id (used for deletion)",
    )

    customer_note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional note from the customer",
    )

    status: str = Field(
        default="verification_pending",
        pattern="^(verification_pending|verified|rejected)$",
        description="Verification status",
    )

    verified_by: Optional[PyObjectId] = Field(
        default=None,
        description="Admin user ID who verified",
    )

    verified_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when verified",
    )

    rejection_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason if rejected",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


# ============================================================
# PAYMENT PROOF VERIFY REQUEST (Admin)
# ============================================================
class PaymentProofVerify(BaseModel):
    """
    Admin verification request.
    """

    upi_reference: str = Field(
        ...,
        min_length=4,
        max_length=100,
        description="UPI transaction reference number from the screenshot",
    )


# ============================================================
# PAYMENT PROOF REJECT REQUEST (Admin)
# ============================================================
class PaymentProofReject(BaseModel):
    """
    Admin rejection request.
    """

    rejection_reason: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Reason for rejecting the payment",
    )


# ============================================================
# PAYMENT PROOF RESPONSE
# ============================================================
class PaymentProofResponse(BaseModel):
    """
    Payment proof response model.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    id: str
    order: str
    user: str
    order_number: Optional[str] = None
    total_price: Optional[float] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    screenshot_url: str
    customer_note: Optional[str] = None
    status: str
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime