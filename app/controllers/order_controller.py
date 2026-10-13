from datetime import datetime
import random
import string
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status
from fastapi import UploadFile

from app.config.database import get_database
from app.models.order import OrderCreate, OrderUpdate
from app.middleware.upload import upload_payment_proof
from app.config.cloudinary import delete_image

from app.services.notification_service import (
    notify_order_created,
    notify_order_shipped,
    notify_order_delivered,
    notify_payment_verified,
    notify_payment_rejected,
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def generate_order_number() -> str:
    """
    Generate a unique order number.
    """
    prefix = "ORD"
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_chars = ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=6,
        )
    )
    return f"{prefix}-{timestamp}-{random_chars}"


def convert_objectid_to_str(obj):
    """
    Recursively convert ObjectId to string in a dictionary or list.
    """
    if isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj


def normalize_id(doc: dict) -> dict:
    """
    Ensure document has an 'id' field (string) and no leftover raw '_id' ObjectId.
    Safe to call after convert_objectid_to_str().
    """
    if "_id" in doc:
        doc["id"] = doc.pop("_id")
    return doc


# ============================================================
# CREATE ORDER
# ============================================================

async def create_order(
    user_id: str,
    order_data: OrderCreate,
) -> dict:
    """
    Create a new order from cart.
    """
    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    # Get user's cart
    cart = await db.carts.find_one(
        {
            "user": ObjectId(user_id)
        }
    )

    if not cart or not cart.get("items"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    # Get user profile for address
    user = await db.users.find_one(
        {
            "_id": ObjectId(user_id)
        }
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Process cart items
    order_items = []
    items_price = 0.0
    product_updates = []

    for item in cart["items"]:
        product = await db.products.find_one(
            {
                "_id": item["product"],
                "is_active": True,
            }
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product not found or inactive",
            )

        # Check stock
        if product["stock"] < item["quantity"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product['name']}. Available: {product['stock']}",
            )

        # Get price (use discount price if available)
        price = product.get("discount_price") or product.get("price", 0)
        total = price * item["quantity"]

        order_items.append({
            "product": product["_id"],
            "name": product["name"],
            "price": price,
            "quantity": item["quantity"],
            "image": product["main_image"],
        })

        items_price += total

        # Prepare stock update
        product_updates.append({
            "product_id": product["_id"],
            "new_stock": product["stock"] - item["quantity"],
        })

    # Calculate prices
    tax_price = round(items_price * 0.10, 2)
    shipping_price = 0.0 if items_price > 100 else 10.0
    total_price = items_price + tax_price + shipping_price

    # Create order
    now = datetime.utcnow()

    order_dict = {
        "user": ObjectId(user_id),
        "items": order_items,
        "shipping_address": order_data.shipping_address.model_dump(),
        "payment_method": order_data.payment_method,
        "payment_status": "pending",
        "payment_proof": None,
        "upi_reference": None,
        "verified_by": None,
        "verified_at": None,
        "rejection_reason": None,
        "items_price": round(items_price, 2),
        "tax_price": tax_price,
        "shipping_price": shipping_price,
        "total_price": round(total_price, 2),
        "is_paid": False,
        "is_delivered": False,
        "status": "pending",
        "order_number": generate_order_number(),
        "created_at": now,
        "updated_at": now,
    }

    # Insert order
    result = await db.orders.insert_one(order_dict)

    # Update product stock
    for update in product_updates:
        await db.products.update_one(
            {
                "_id": update["product_id"]
            },
            {
                "$set": {
                    "stock": update["new_stock"]
                }
            }
        )

    # Clear cart
    await db.carts.update_one(
        {
            "user": ObjectId(user_id)
        },
        {
            "$set": {
                "items": [],
                "updated_at": now,
            }
        }
    )

    # Fetch created order
    created_order = await db.orders.find_one(
        {
            "_id": result.inserted_id
        }
    )

    if not created_order:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order",
        )

    # CONVERT ALL ObjectId TO STRING + normalize _id → id
    created_order = convert_objectid_to_str(created_order)
    created_order = normalize_id(created_order)

    # Send notification
    try:
        await notify_order_created(
            str(user["_id"]),
            {
                "id": str(result.inserted_id),
                "order_number": order_dict["order_number"],
                "total_price": round(total_price, 2),
                "status": "pending",
            }
        )
        print("✅ Order notification sent successfully")
    except Exception as error:
        print(f"⚠️ Order notification failed: {str(error)}")

    return {
        "success": True,
        "message": "Order created successfully",
        "order": created_order,
    }


# ============================================================
# GET USER ORDERS
# ============================================================

async def get_user_orders(
    user_id: str,
    page: int = 1,
    limit: int = 10,
) -> dict:
    """
    Get all orders for a user.
    """
    db = get_database()

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    skip = (page - 1) * limit

    orders_cursor = db.orders.find(
        {
            "user": ObjectId(user_id)
        }
    ).sort(
        "created_at",
        -1
    ).skip(
        skip
    ).limit(
        limit
    )

    orders = await orders_cursor.to_list(length=limit)

    # Convert + normalize
    orders = convert_objectid_to_str(orders)
    orders = [normalize_id(o) for o in orders]

    total = await db.orders.count_documents(
        {
            "user": ObjectId(user_id)
        }
    )

    return {
        "success": True,
        "orders": orders,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# ============================================================
# GET ORDER BY ID
# ============================================================

async def get_order_by_id(
    user_id: str,
    order_id: str,
) -> dict:
    """
    Get a specific order by ID.
    """
    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id),
            "user": ObjectId(user_id),
        }
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    order = convert_objectid_to_str(order)
    order = normalize_id(order)

    return {
        "success": True,
        "order": order,
    }


# ============================================================
# ADMIN: GET ALL ORDERS
# ============================================================

async def admin_get_orders(
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> dict:
    """
    Get all orders (admin only).
    """
    db = get_database()

    query = {}

    if status:
        query["status"] = status

    if search:
        query["$or"] = [
            {"order_number": {"$regex": search, "$options": "i"}},
        ]

    skip = (page - 1) * limit

    orders_cursor = db.orders.find(
        query
    ).sort(
        "created_at",
        -1
    ).skip(
        skip
    ).limit(
        limit
    )

    orders = await orders_cursor.to_list(length=limit)

    # Enrich + convert
    enriched = []
    for order in orders:
        user_id_obj = order.get("user")

        # Only query user if it's a valid ObjectId
        if isinstance(user_id_obj, ObjectId):
            user = await db.users.find_one({"_id": user_id_obj})
            if user:
                order["user_name"] = user.get("name", "Unknown")
                order["user_email"] = user.get("email", "Unknown")

        # Convert + normalize
        order = convert_objectid_to_str(order)
        order = normalize_id(order)

        enriched.append(order)

    total = await db.orders.count_documents(query)

    return {
        "success": True,
        "orders": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# ============================================================
# ADMIN: UPDATE ORDER
# ============================================================

async def admin_update_order(
    order_id: str,
    update_data: OrderUpdate,
) -> dict:
    """
    Update order status (admin only).
    """
    db = get_database()

    if not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID",
        )

    order_object_id = ObjectId(order_id)

    order = await db.orders.find_one(
        {
            "_id": order_object_id
        }
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    update_dict = {}
    now = datetime.utcnow()

    if update_data.status is not None:
        update_dict["status"] = update_data.status

        if update_data.status == "delivered":
            update_dict["is_delivered"] = True
            update_dict["delivered_at"] = now
        elif update_data.status == "shipped":
            update_dict["is_delivered"] = False

    if update_data.is_paid is not None:
        update_dict["is_paid"] = update_data.is_paid
        if update_data.is_paid:
            update_dict["paid_at"] = now

    if update_data.is_delivered is not None:
        update_dict["is_delivered"] = update_data.is_delivered
        if update_data.is_delivered:
            update_dict["delivered_at"] = now

    if update_data.payment_result is not None:
        update_dict["payment_result"] = update_data.payment_result.dict()

    update_dict["updated_at"] = now

    await db.orders.update_one(
        {
            "_id": order_object_id
        },
        {
            "$set": update_dict
        }
    )

    # Send status notifications
    if update_data.status == "shipped":
        try:
            await notify_order_shipped(
                str(order["user"]),
                str(order["_id"]),
            )
            print(f"✅ Shipping notification sent for order {order_id}")
        except Exception as e:
            print(f"⚠️ Shipping notification failed: {str(e)}")
    elif update_data.status == "delivered":
        try:
            await notify_order_delivered(
                str(order["user"]),
                str(order["_id"]),
            )
            print(f"✅ Delivery notification sent for order {order_id}")
        except Exception as e:
            print(f"⚠️ Delivery notification failed: {str(e)}")

    updated_order = await db.orders.find_one(
        {
            "_id": order_object_id
        }
    )

    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order updated but could not be retrieved",
        )

    updated_order = convert_objectid_to_str(updated_order)
    updated_order = normalize_id(updated_order)

    return {
        "success": True,
        "message": "Order updated successfully",
        "order": updated_order,
    }


# ============================================================
# CUSTOMER: SUBMIT PAYMENT PROOF
# ============================================================

async def submit_payment_proof(
    user_id: str,
    order_id: str,
    screenshot_file: UploadFile,
    customer_note: Optional[str] = None,
) -> dict:
    """
    Customer submits UPI payment screenshot for verification.
    """
    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id),
            "user": ObjectId(user_id),
        }
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.get("payment_method") != "upi":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment proof is only for UPI orders",
        )

    current_status = order.get("payment_status", "pending")
    if current_status == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already verified",
        )

    try:
        upload_result = await upload_payment_proof(screenshot_file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload screenshot: {str(e)}",
        )

    screenshot_url = upload_result.get("url")
    screenshot_public_id = upload_result.get("public_id")

    if not screenshot_url or not screenshot_public_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary did not return a valid response",
        )

    now = datetime.utcnow()

    existing_proof = await db.payment_proofs.find_one(
        {"order": ObjectId(order_id)}
    )

    if existing_proof:
        try:
            await delete_image(existing_proof["screenshot_public_id"])
        except Exception as e:
            print(f"⚠️ Failed to delete old screenshot: {e}")

    proof_dict = {
        "order": ObjectId(order_id),
        "user": ObjectId(user_id),
        "screenshot_url": screenshot_url,
        "screenshot_public_id": screenshot_public_id,
        "customer_note": customer_note,
        "status": "verification_pending",
        "verified_by": None,
        "verified_at": None,
        "rejection_reason": None,
        "created_at": now,
        "updated_at": now,
    }

    if existing_proof:
        await db.payment_proofs.update_one(
            {"_id": existing_proof["_id"]},
            {"$set": proof_dict},
        )
        proof_id = str(existing_proof["_id"])
    else:
        result = await db.payment_proofs.insert_one(proof_dict)
        proof_id = str(result.inserted_id)

    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "payment_status": "verification_pending",
                "payment_proof": {
                    "screenshot_url": screenshot_url,
                    "public_id": screenshot_public_id,
                    "submitted_at": now,
                    "note": customer_note,
                },
                "updated_at": now,
            }
        },
    )

    return {
        "success": True,
        "message": "Payment proof submitted. Awaiting verification.",
        "proof_id": proof_id,
    }


# ============================================================
# CUSTOMER: GET PAYMENT PROOF STATUS
# ============================================================

async def get_payment_proof(
    user_id: str,
    order_id: str,
) -> dict:
    """
    Get payment proof details for an order.
    """
    db = get_database()

    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id),
            "user": ObjectId(user_id),
        }
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    proof = await db.payment_proofs.find_one(
        {"order": ObjectId(order_id)}
    )

    if proof:
        proof = convert_objectid_to_str(proof)
        proof = normalize_id(proof)

    return {
        "success": True,
        "payment_status": order.get("payment_status", "pending"),
        "order_number": order.get("order_number"),
        "total_price": order.get("total_price"),
        "proof": proof,
        "upi_reference": order.get("upi_reference"),
        "rejection_reason": order.get("rejection_reason"),
    }


# ============================================================
# ADMIN: GET PENDING PAYMENTS
# ============================================================

async def admin_get_pending_payments(
    page: int = 1,
    limit: int = 20,
    status_filter: str = "verification_pending",
) -> dict:
    """
    Get all payment proofs for admin verification.
    """
    db = get_database()

    query = {}
    if status_filter and status_filter != "all":
        query["status"] = status_filter

    skip = (page - 1) * limit

    proofs_cursor = (
        db.payment_proofs.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    proofs = await proofs_cursor.to_list(length=limit)

    enriched = []
    for proof in proofs:
        order = await db.orders.find_one({"_id": proof["order"]})
        user = await db.users.find_one({"_id": proof["user"]})

        enriched.append({
            "id": str(proof["_id"]),
            "order_id": str(proof["order"]),
            "order_number": order.get("order_number") if order else None,
            "total_price": order.get("total_price") if order else None,
            "user_name": user.get("name") if user else "Unknown",
            "user_email": user.get("email") if user else "Unknown",
            "screenshot_url": proof["screenshot_url"],
            "customer_note": proof.get("customer_note"),
            "status": proof["status"],
            "created_at": proof["created_at"],
            "verified_at": proof.get("verified_at"),
            "rejection_reason": proof.get("rejection_reason"),
        })

    total = await db.payment_proofs.count_documents(query)

    return {
        "success": True,
        "proofs": enriched,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        },
    }


# ============================================================
# ADMIN: VERIFY PAYMENT
# ============================================================

async def admin_verify_payment(
    admin_id: str,
    proof_id: str,
    upi_reference: str,
) -> dict:
    """
    Admin verifies a payment proof.
    """
    db = get_database()

    if not ObjectId.is_valid(proof_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid proof ID",
        )

    proof = await db.payment_proofs.find_one(
        {"_id": ObjectId(proof_id)}
    )

    if not proof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proof not found",
        )

    if proof["status"] == "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already verified",
        )

    now = datetime.utcnow()

    await db.payment_proofs.update_one(
        {"_id": ObjectId(proof_id)},
        {
            "$set": {
                "status": "verified",
                "verified_by": ObjectId(admin_id),
                "verified_at": now,
                "updated_at": now,
            }
        },
    )

    await db.orders.update_one(
        {"_id": proof["order"]},
        {
            "$set": {
                "payment_status": "verified",
                "is_paid": True,
                "paid_at": now,
                "upi_reference": upi_reference,
                "status": "processing",
                "verified_by": ObjectId(admin_id),
                "verified_at": now,
                "updated_at": now,
            }
        },
    )

    try:
        await notify_payment_verified(str(proof["order"]))
    except Exception as e:
        print(f"⚠️ Payment verified notification failed: {e}")

    return {
        "success": True,
        "message": "Payment verified successfully",
    }


# ============================================================
# ADMIN: REJECT PAYMENT
# ============================================================

async def admin_reject_payment(
    admin_id: str,
    proof_id: str,
    rejection_reason: str,
) -> dict:
    """
    Admin rejects a payment proof.
    """
    db = get_database()

    if not ObjectId.is_valid(proof_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid proof ID",
        )

    proof = await db.payment_proofs.find_one(
        {"_id": ObjectId(proof_id)}
    )

    if not proof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment proof not found",
        )

    now = datetime.utcnow()

    await db.payment_proofs.update_one(
        {"_id": ObjectId(proof_id)},
        {
            "$set": {
                "status": "rejected",
                "verified_by": ObjectId(admin_id),
                "verified_at": now,
                "rejection_reason": rejection_reason,
                "updated_at": now,
            }
        },
    )

    await db.orders.update_one(
        {"_id": proof["order"]},
        {
            "$set": {
                "payment_status": "rejected",
                "rejection_reason": rejection_reason,
                "status": "cancelled",
                "verified_by": ObjectId(admin_id),
                "verified_at": now,
                "updated_at": now,
            }
        },
    )

    # Restore product stock
    order = await db.orders.find_one({"_id": proof["order"]})
    if order:
        for item in order.get("items", []):
            await db.products.update_one(
                {"_id": item["product"]},
                {"$inc": {"stock": item["quantity"]}},
            )

    try:
        await notify_payment_rejected(str(proof["order"]), rejection_reason)
    except Exception as e:
        print(f"⚠️ Payment rejection notification failed: {e}")

    return {
        "success": True,
        "message": "Payment rejected and stock restored",
    }