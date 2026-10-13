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

    # Get user count
    total_users = await db.users.count_documents(
        {
            "is_active": True
        }
    )

    # Get product count
    total_products = await db.products.count_documents(
        {
            "is_active": True
        }
    )

    # Get category count
    total_categories = await db.categories.count_documents(
        {
            "is_active": True
        }
    )

    # Get order statistics
    total_orders = await db.orders.count_documents({})
    pending_orders = await db.orders.count_documents(
        {
            "status": "pending"
        }
    )
    processing_orders = await db.orders.count_documents(
        {
            "status": "processing"
        }
    )
    shipped_orders = await db.orders.count_documents(
        {
            "status": "shipped"
        }
    )
    delivered_orders = await db.orders.count_documents(
        {
            "status": "delivered"
        }
    )

    # Get revenue
    revenue_pipeline = [
        {
            "$match": {
                "is_paid": True
            }
        },
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"},
                "total_orders": {"$sum": 1},
            }
        }
    ]
    
    revenue_result = await db.orders.aggregate(
        revenue_pipeline
    ).to_list(length=1)
    
    total_revenue = revenue_result[0]["total_revenue"] if revenue_result else 0

    # Get recent orders
    recent_orders = await db.orders.find(
        {}
    ).sort(
        "created_at",
        -1
    ).limit(
        10
    ).to_list(
        length=10
    )

    # Format recent orders
    formatted_orders = []
    for order in recent_orders:
        # Get user details
        user = await db.users.find_one(
            {
                "_id": order["user"]
            }
        )
        
        formatted_orders.append({
            "id": str(order["_id"]),
            "order_number": order.get("order_number"),
            "user_name": user.get("name") if user else "Unknown",
            "user_email": user.get("email") if user else "Unknown",
            "total_price": order["total_price"],
            "status": order["status"],
            "created_at": order["created_at"],
        })

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
            },
            "revenue": {
                "total": round(total_revenue, 2),
                "currency": "USD",
            },
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
        # Get last 30 days sales
        for i in range(30):
            date = now - timedelta(days=i)
            start = datetime(date.year, date.month, date.day, 0, 0, 0)
            end = datetime(date.year, date.month, date.day, 23, 59, 59)

            sales = await get_daily_sales(start, end)
            sales_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "sales": sales,
            })

    elif period == "weekly":
        # Get last 12 weeks sales
        for i in range(12):
            date = now - timedelta(weeks=i)
            start = date - timedelta(days=date.weekday())
            start = datetime(start.year, start.month, start.day, 0, 0, 0)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            sales = await get_daily_sales(start, end)
            sales_data.append({
                "week": f"Week {i + 1}",
                "date": f"{start.strftime('%b %d')} - {end.strftime('%b %d')}",
                "sales": sales,
            })

    elif period == "monthly":
        # Get last 12 months sales — FIXED: properly handles month/year rollover
        for i in range(12):
            # Calculate target month and year
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
            sales_data.append({
                "month": date.strftime("%b %Y"),
                "sales": sales,
            })

    return {
        "success": True,
        "period": period,
        "data": sales_data,
    }


async def get_daily_sales(start: datetime, end: datetime) -> dict:
    """
    Get sales data for a specific date range.
    """
    db = get_database()
    
    # Get orders
    orders = await db.orders.find(
        {
            "created_at": {"$gte": start, "$lte": end},
            "is_paid": True,
        }
    ).to_list(length=1000)
    
    total_revenue = sum(order["total_price"] for order in orders)
    total_orders = len(orders)
    
    # Get top products
    product_sales = {}
    for order in orders:
        for item in order.get("items", []):
            product_id = str(item["product"])
            if product_id not in product_sales:
                product_sales[product_id] = {
                    "product_id": product_id,
                    "name": item["name"],
                    "quantity": 0,
                    "revenue": 0,
                }
            product_sales[product_id]["quantity"] += item["quantity"]
            product_sales[product_id]["revenue"] += item["price"] * item["quantity"]
    
    top_products = sorted(
        product_sales.values(),
        key=lambda x: x["revenue"],
        reverse=True
    )[:5]
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "total_items": sum(sum(item["quantity"] for item in order.get("items", [])) for order in orders),
        "average_order_value": round(total_revenue / total_orders, 2) if total_orders > 0 else 0,
        "top_products": top_products,
    }