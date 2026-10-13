from fastapi import APIRouter, Depends, Query, File, Form, UploadFile
from typing import Optional

from app.controllers.order_controller import (
    create_order,
    get_user_orders,
    get_order_by_id,
    admin_get_orders,
    admin_update_order,
    # NEW: Manual UPI payment functions
    submit_payment_proof,
    get_payment_proof,
    admin_get_pending_payments,
    admin_verify_payment,
    admin_reject_payment,
)

from app.models.order import (
    OrderCreate,
    OrderUpdate,
)

from app.models.payment_proof import (
    PaymentProofVerify,
    PaymentProofReject,
)

from app.middleware.auth import (
    JWTBearer,
    get_current_user,
    get_current_admin,
)

router = APIRouter()

# IMPORTANT: ADMIN ROUTES MUST COME BEFORE DYNAMIC ROUTES


# ============================================================
# USER: CREATE ORDER
# ============================================================

@router.post(
    "/",
    tags=["Orders"],
    dependencies=[Depends(JWTBearer())],
)
async def create_new_order(
    order_data: OrderCreate,
    user: dict = Depends(get_current_user),
):
    return await create_order(
        user["id"],
        order_data,
    )


# ============================================================
# USER: GET ORDERS
# ============================================================

@router.get(
    "/",
    tags=["Orders"],
    dependencies=[Depends(JWTBearer())],
)
async def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    return await get_user_orders(
        user["id"],
        page,
        limit,
    )


# ============================================================
# ADMIN: PAYMENT VERIFICATION ROUTES
# (MUST COME BEFORE DYNAMIC /{order_id})
# ============================================================

# ------------------------------------------------------------
# ADMIN: GET PENDING PAYMENTS
# ------------------------------------------------------------

@router.get(
    "/admin/payments/pending",
    tags=["Orders", "Admin Payments"],
    dependencies=[Depends(JWTBearer())],
)
async def admin_get_pending_payments_route(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query(
        "verification_pending",
        description="verification_pending | verified | rejected | all",
    ),
    admin_id: str = Depends(get_current_admin),
):
    """
    Get all payment proofs for admin verification.
    """
    return await admin_get_pending_payments(
        page,
        limit,
        status_filter,
    )


# ------------------------------------------------------------
# ADMIN: VERIFY PAYMENT
# ------------------------------------------------------------

@router.post(
    "/admin/payments/{proof_id}/verify",
    tags=["Orders", "Admin Payments"],
    dependencies=[Depends(JWTBearer())],
)
async def admin_verify_payment_route(
    proof_id: str,
    verify_data: PaymentProofVerify,
    admin_id: str = Depends(get_current_admin),
):
    """
    Verify a UPI payment proof.
    """
    return await admin_verify_payment(
        admin_id,
        proof_id,
        verify_data.upi_reference,
    )


# ------------------------------------------------------------
# ADMIN: REJECT PAYMENT
# ------------------------------------------------------------

@router.post(
    "/admin/payments/{proof_id}/reject",
    tags=["Orders", "Admin Payments"],
    dependencies=[Depends(JWTBearer())],
)
async def admin_reject_payment_route(
    proof_id: str,
    reject_data: PaymentProofReject,
    admin_id: str = Depends(get_current_admin),
):
    """
    Reject a UPI payment proof with a reason.
    """
    return await admin_reject_payment(
        admin_id,
        proof_id,
        reject_data.rejection_reason,
    )


# ============================================================
# ADMIN: GET ALL ORDERS - MUST COME BEFORE /{order_id}
# ============================================================

@router.get(
    "/admin/all",
    tags=["Orders"],
    dependencies=[Depends(JWTBearer())],
)
async def admin_get_all_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    admin_id: str = Depends(get_current_admin),
):
    return await admin_get_orders(
        page,
        limit,
        status,
        search,
    )


# ============================================================
# ADMIN: UPDATE ORDER
# ============================================================

@router.put(
    "/admin/{order_id}",
    tags=["Orders"],
    dependencies=[Depends(JWTBearer())],
)
async def admin_update_order_status(
    order_id: str,
    update_data: OrderUpdate,
    admin_id: str = Depends(get_current_admin),
):
    return await admin_update_order(
        order_id,
        update_data,
    )


# ============================================================
# USER: PAYMENT PROOF ROUTES
# (Specific path segments — before /{order_id})
# ============================================================

# ------------------------------------------------------------
# USER: SUBMIT PAYMENT PROOF (UPLOAD SCREENSHOT)
# ------------------------------------------------------------

@router.post(
    "/{order_id}/submit-payment-proof",
    tags=["Orders", "Payments"],
    dependencies=[Depends(JWTBearer())],
)
async def submit_payment_proof_route(
    order_id: str,
    screenshot: UploadFile = File(..., description="UPI payment screenshot (JPG/PNG, max 3MB)"),
    customer_note: Optional[str] = Form(None, max_length=500),
    user: dict = Depends(get_current_user),
):
    """
    Customer uploads UPI payment screenshot for admin verification.
    """
    return await submit_payment_proof(
        user["id"],
        order_id,
        screenshot,
        customer_note,
    )


# ------------------------------------------------------------
# USER: GET PAYMENT PROOF STATUS
# ------------------------------------------------------------

@router.get(
    "/{order_id}/payment-proof",
    tags=["Orders", "Payments"],
    dependencies=[Depends(JWTBearer())],
)
async def get_payment_proof_route(
    order_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get payment proof status for an order.
    """
    return await get_payment_proof(
        user["id"],
        order_id,
    )


# ============================================================
# USER: GET SINGLE ORDER - KEEP THIS LAST
# ============================================================

@router.get(
    "/{order_id}",
    tags=["Orders"],
    dependencies=[Depends(JWTBearer())],
)
async def get_order(
    order_id: str,
    user: dict = Depends(get_current_user),
):
    return await get_order_by_id(
        user["id"],
        order_id,
    )