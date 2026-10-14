from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.config.database import get_database


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

async def get_dashboard_stats() -> dict:
    """
    Get admin dashboard statistics.
    """
    db = get_database()

    # --------------------------------------------------------
    # USER / PRODUCT / CATEGORY COUNTS
    # --------------------------------------------------------
    total_users = await db.users.count_documents({"is_active": True})
    total_products = await db.products.count_documents({"is_active": True})
    total_categories = await db.categories.count_documents({"is_active": True})

    # --------------------------------------------------------
    # ORDER STATISTICS
    # --------------------------------------------------------
    total_orders = await db.orders.count_documents({})
    pending_orders = await db.orders.count_documents({"status": "pending"})
    processing_orders = await db.orders.count_documents({"status": "processing"})
    shipped_orders = await db.orders.count_documents({"status": "shipped"})
    delivered_orders = await db.orders.count_documents({"status": "delivered"})
    cancelled_orders = await db.orders.count_documents({"status": "cancelled"})

    # --------------------------------------------------------
    # REVENUE (only from PAID orders)
    # --------------------------------------------------------
    revenue_pipeline = [
        {"$match": {"is_paid": True}},
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"},
                "total_orders": {"$sum": 1},
            }
        },
    ]

    revenue_result = await db.orders.aggregate(revenue_pipeline).to_list(length=1)
    total_revenue = revenue_result[0]["total_revenue"] if revenue_result else 0

    # --------------------------------------------------------
    # PAYMENT HEALTH (Manual UPI verification)
    # --------------------------------------------------------
    verified_payments = await db.payment_proofs.count_documents(
        {"status": "verified"}
    )
    pending_payments = await db.payment_proofs.count_documents(
        {"status": "verification_pending"}
    )
    rejected_payments = await db.payment_proofs.count_documents(
        {"status": "rejected"}
    )

    # Sum of verified order amounts
    verified_amount_pipeline = [
        {"$match": {"payment_status": "verified"}},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$total_price"},
            }
        },
    ]
    verified_amount_result = await db.orders.aggregate(
        verified_amount_pipeline
    ).to_list(length=1)
    verified_amount = (
        float(verified_amount_result[0]["total"]) if verified_amount_result else 0.0
    )

    # --------------------------------------------------------
    # LOW STOCK PRODUCTS (stock <= 5)
    # --------------------------------------------------------
    low_stock_cursor = (
        db.products.find({"stock": {"$lte": 5}, "is_active": True})
        .sort("stock", 1)
        .limit(5)
    )
    low_stock_products = []
    async for product in low_stock_cursor:
        low_stock_products.append(
            {
                "id": str(product["_id"]),
                "name": product.get("name", "Unknown"),
                "stock": int(product.get("stock", 0)),
            }
        )

    # --------------------------------------------------------
    # RECENT ORDERS
    # --------------------------------------------------------
    recent_orders = (
        await db.orders.find({})
        .sort("created_at", -1)
        .limit(10)
        .to_list(length=10)
    )

    formatted_orders = []
    for order in recent_orders:
        user = await db.users.find_one({"_id": order["user"]})

        formatted_orders.append(
            {
                "id": str(order["_id"]),
                "order_number": order.get("order_number"),
                "user_name": user.get("name") if user else "Unknown",
                "user_email": user.get("email") if user else "Unknown",
                "total_price": order["total_price"],
                "status": order["status"],
                "payment_status": order.get("payment_status", "pending"),
                "created_at": order["created_at"],
            }
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------
    return {
        "success": True,
        "stats": {
            "users": total_users,
            "products": total_products,
            "categories": total_categories,
            "orders": {
                "total": total_orders,
                "pending": pending_orders,
                "processing": processing_orders,
                "shipped": shipped_orders,
                "delivered": delivered_orders,
                "cancelled": cancelled_orders,
            },
            "revenue": {
                "total": round(total_revenue, 2),
                "currency": "INR",
            },
            "payments": {
                "verified": verified_payments,
                "pending": pending_payments,
                "rejected": rejected_payments,
                "verified_amount": round(verified_amount, 2),
            },
            "low_stock_products": low_stock_products,
        },
        "recent_orders": formatted_orders,
    }


# ============================================================
# SALES ANALYTICS
# ============================================================

async def get_sales_analytics(
    period: str = "monthly",
    year: int = None,
    month: int = None,
) -> dict:
    """
    Get sales analytics by period.
    """
    db = get_database()

    now = datetime.utcnow()
    current_year = year or now.year
    current_month = month or now.month

    sales_data = []

    if period == "daily":
        # Last 30 days sales (most recent first, then reverse for chart)
        for i in range(30):
            date = now - timedelta(days=i)
            start = datetime(date.year, date.month, date.day, 0, 0, 0)
            end = datetime(date.year, date.month, date.day, 23, 59, 59)

            sales = await get_daily_sales(start, end)
            sales_data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "sales": sales,
                }
            )
        sales_data.reverse()

    elif period == "weekly":
        # Last 12 weeks sales
        for i in range(12):
            date = now - timedelta(weeks=i)
            start_of_week = date - timedelta(days=date.weekday())
            start = datetime(
                start_of_week.year, start_of_week.month, start_of_week.day, 0, 0, 0
            )
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            sales = await get_daily_sales(start, end)
            sales_data.append(
                {
                    "week": f"Week {i + 1}",
                    "date": f"{start.strftime('%b %d')} - {end.strftime('%b %d')}",
                    "sales": sales,
                }
            )
        sales_data.reverse()

    elif period == "monthly":
        # Last 12 months sales — handles month/year rollover
        for i in range(12):
            target_month = current_month - i
            target_year = current_year

            # Roll back the year if month goes below 1
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            # Roll forward the year if month goes above 12
            while target_month > 12:
                target_month -= 12
                target_year += 1

            date = datetime(target_year, target_month, 1)

            start = datetime(date.year, date.month, 1)
            if date.month == 12:
                end = datetime(date.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(date.year, date.month + 1, 1) - timedelta(seconds=1)

            sales = await get_daily_sales(start, end)
            sales_data.append(
                {
                    "month": date.strftime("%b %Y"),
                    "sales": sales,
                }
            )
        sales_data.reverse()

    return {
        "success": True,
        "period": period,
        "data": sales_data,
    }


# ============================================================
# HELPER: DAILY SALES
# ============================================================

async def get_daily_sales(start: datetime, end: datetime) -> dict:
    """
    Get sales data for a specific date range.
    """
    db = get_database()

    # Get paid orders in range
    orders = await db.orders.find(
        {
            "created_at": {"$gte": start, "$lte": end},
            "is_paid": True,
        }
    ).to_list(length=1000)

    total_revenue = sum(order.get("total_price", 0) for order in orders)
    total_orders = len(orders)
    total_items = sum(
        sum(item.get("quantity", 0) for item in order.get("items", []))
        for order in orders
    )

    # Aggregate top products
    product_sales = {}
    for order in orders:
        for item in order.get("items", []):
            product_id = str(item.get("product"))
            if product_id not in product_sales:
                product_sales[product_id] = {
                    "product_id": product_id,
                    "name": item.get("name", "Unknown"),
                    "quantity": 0,
                    "revenue": 0,
                }
            product_sales[product_id]["quantity"] += item.get("quantity", 0)
            product_sales[product_id]["revenue"] += item.get("price", 0) * item.get(
                "quantity", 0
            )

    top_products = sorted(
        product_sales.values(),
        key=lambda x: x["revenue"],
        reverse=True,
    )[:5]

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_items": total_items,
        "average_order_value": (
            round(total_revenue / total_orders, 2) if total_orders > 0 else 0
        ),
        "top_products": top_products,
    }