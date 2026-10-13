from datetime import datetime
from typing import Optional, List, Any
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
# ORDER ITEM
# ============================================================
class OrderItem(BaseModel):
    """
    Order item model.
    """

    product: PyObjectId = Field(
        ...,
        description="Product ID",
    )

    name: str = Field(
        ...,
        description="Product name",
    )

    price: float = Field(
        ...,
        gt=0,
        description="Product price",
    )

    quantity: int = Field(
        ...,
        ge=1,
        description="Quantity",
    )

    image: str = Field(
        ...,
        description="Product image URL",
    )


# ============================================================
# SHIPPING ADDRESS
# ============================================================
class ShippingAddress(BaseModel):
    """
    Shipping address model.
    """

    street: str = Field(
        ...,
        min_length=3,
        max_length=200,
    )

    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    zip_code: str = Field(
        ...,
        min_length=3,
        max_length=20,
    )

    country: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )


# ============================================================
# PAYMENT RESULT
# ============================================================
class PaymentResult(BaseModel):
    """
    Payment result model.
    """

    id: Optional[str] = None
    status: Optional[str] = None
    update_time: Optional[str] = None
    email_address: Optional[str] = None


# ============================================================
# PAYMENT PROOF
# ============================================================
class PaymentProof(BaseModel):
    """
    UPI payment screenshot proof.
    """

    screenshot_url: Optional[str] = None
    public_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    note: Optional[str] = None


# ============================================================
# ORDER MODEL
# ============================================================
class Order(BaseModel):
    """
    Order database model.
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

    items: List[OrderItem] = Field(
        ...,
        description="Order items",
    )

    shipping_address: ShippingAddress = Field(
        ...,
        description="Shipping address",
    )

    # --------------------------------------------------------
    # PAYMENT METHOD — UPI or COD only
    # --------------------------------------------------------
    payment_method: str = Field(
        ...,
        pattern="^(upi|cash_on_delivery)$",
        description="Payment method: upi or cash_on_delivery",
    )

    payment_result: Optional[PaymentResult] = None

    # --------------------------------------------------------
    # MANUAL UPI PAYMENT TRACKING
    # --------------------------------------------------------
    payment_status: str = Field(
        default="pending",
        pattern="^(pending|verification_pending|verified|rejected|refunded)$",
        description="Manual UPI payment status",
    )

    payment_proof: Optional[PaymentProof] = None

    upi_reference: Optional[str] = Field(
        default=None,
        description="UPI transaction reference number (entered by admin)",
    )

    verified_by: Optional[str] = Field(
        default=None,
        description="Admin user ID who verified the payment",
    )

    verified_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when payment was verified",
    )

    rejection_reason: Optional[str] = Field(
        default=None,
        description="Reason if payment was rejected",
    )

    # --------------------------------------------------------
    # PRICING
    # --------------------------------------------------------
    items_price: float = Field(
        ...,
        ge=0,
        description="Total items price",
    )

    tax_price: float = Field(
        default=0.0,
        ge=0,
        description="Tax price",
    )

    shipping_price: float = Field(
        default=0.0,
        ge=0,
        description="Shipping price",
    )

    total_price: float = Field(
        ...,
        ge=0,
        description="Total order price",
    )

    # --------------------------------------------------------
    # ORDER STATE
    # --------------------------------------------------------
    is_paid: bool = Field(
        default=False,
        description="Is order paid",
    )

    paid_at: Optional[datetime] = None

    is_delivered: bool = Field(
        default=False,
        description="Is order delivered",
    )

    delivered_at: Optional[datetime] = None

    status: str = Field(
        default="pending",
        pattern="^(pending|processing|shipped|delivered|cancelled)$",
        description="Order status",
    )

    order_number: Optional[str] = None

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


# ============================================================
# ORDER CREATE REQUEST
# ============================================================
class OrderCreate(BaseModel):
    """
    Order creation request.
    """

    shipping_address: ShippingAddress

    payment_method: str = Field(
        ...,
        pattern="^(upi|cash_on_delivery)$",
    )


# ============================================================
# ORDER UPDATE REQUEST (Admin)
# ============================================================
class OrderUpdate(BaseModel):
    """
    Order update request.
    """

    status: Optional[str] = Field(
        default=None,
        pattern="^(pending|processing|shipped|delivered|cancelled)$",
    )

    is_paid: Optional[bool] = None

    is_delivered: Optional[bool] = None

    payment_status: Optional[str] = Field(
        default=None,
        pattern="^(pending|verification_pending|verified|rejected|refunded)$",
    )

    upi_reference: Optional[str] = None

    rejection_reason: Optional[str] = None

    payment_result: Optional[PaymentResult] = None