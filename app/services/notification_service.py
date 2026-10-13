from app.services.websocket_manager import manager
from app.services.email_service import (
    send_order_confirmation_email,
    send_order_shipped_email,
    send_order_delivered_email,
    send_welcome_email,
    send_payment_verified_email,
    send_payment_rejected_email,
)


# ============================================================
# ORDER NOTIFICATIONS
# ============================================================

async def notify_order_created(
    user_id: str,
    order_data: dict,
) -> None:
    """
    Send order creation notification.
    """
    # Send WebSocket notification
    await manager.send_to_user(
        user_id,
        {
            "type": "order_created",
            "data": {
                "order_id": order_data.get("id"),
                "order_number": order_data.get("order_number"),
                "total_price": order_data.get("total_price"),
                "status": order_data.get("status"),
            },
        }
    )

    # Send email
    await send_order_confirmation_email(order_data.get("id"))


async def notify_order_shipped(
    user_id: str,
    order_id: str,
) -> None:
    """
    Send order shipped notification.
    """
    # Send WebSocket notification
    await manager.send_to_user(
        user_id,
        {
            "type": "order_shipped",
            "data": {
                "order_id": order_id,
                "message": "Your order has been shipped!",
            },
        }
    )

    # Send email
    await send_order_shipped_email(order_id)


async def notify_order_delivered(
    user_id: str,
    order_id: str,
) -> None:
    """
    Send order delivered notification.
    """
    # Send WebSocket notification
    await manager.send_to_user(
        user_id,
        {
            "type": "order_delivered",
            "data": {
                "order_id": order_id,
                "message": "Your order has been delivered!",
            },
        }
    )

    # Send email
    await send_order_delivered_email(order_id)


async def notify_user_welcome(
    user_id: str,
) -> None:
    """
    Send welcome notification.
    """
    # Send WebSocket notification
    await manager.send_to_user(
        user_id,
        {
            "type": "welcome",
            "data": {
                "message": "Welcome to AI Jewellery Shop!",
            },
        }
    )

    # Send email
    await send_welcome_email(user_id)


async def notify_admin(
    message: str,
    data: dict = None,
) -> None:
    """
    Send notification to admin.
    """
    # Broadcast to all (admin will listen)
    await manager.broadcast({
        "type": "admin_notification",
        "data": {
            "message": message,
            "data": data,
        },
    })


# ============================================================
# PAYMENT NOTIFICATIONS (Manual UPI Verification)
# ============================================================

async def notify_payment_verified(
    order_id: str,
) -> None:
    """
    Send notification when admin verifies a UPI payment.
    """
    from app.config.database import get_database
    from bson import ObjectId

    db = get_database()

    if not ObjectId.is_valid(order_id):
        return

    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        return

    user_id = str(order["user"])

    # Send WebSocket notification to customer
    await manager.send_to_user(
        user_id,
        {
            "type": "payment_verified",
            "data": {
                "order_id": order_id,
                "order_number": order.get("order_number"),
                "message": "Your payment has been verified! Order is confirmed.",
            },
        }
    )

    # Notify admins
    await manager.broadcast({
        "type": "admin_notification",
        "data": {
            "message": f"Payment verified for order {order.get('order_number')}",
            "data": {
                "order_id": order_id,
                "order_number": order.get("order_number"),
            },
        },
    })

    # Send email
    await send_payment_verified_email(order_id)


async def notify_payment_rejected(
    order_id: str,
    reason: str,
) -> None:
    """
    Send notification when admin rejects a UPI payment.
    """
    from app.config.database import get_database
    from bson import ObjectId

    db = get_database()

    if not ObjectId.is_valid(order_id):
        return

    order = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        return

    user_id = str(order["user"])

    # Send WebSocket notification to customer
    await manager.send_to_user(
        user_id,
        {
            "type": "payment_rejected",
            "data": {
                "order_id": order_id,
                "order_number": order.get("order_number"),
                "reason": reason,
                "message": "Your payment could not be verified.",
            },
        }
    )

    # Notify admins
    await manager.broadcast({
        "type": "admin_notification",
        "data": {
            "message": f"Payment rejected for order {order.get('order_number')}",
            "data": {
                "order_id": order_id,
                "order_number": order.get("order_number"),
                "reason": reason,
            },
        },
    })

    # Send email
    await send_payment_rejected_email(order_id, reason)