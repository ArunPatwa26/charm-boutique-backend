import os
import httpx
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from bson import ObjectId

from app.config.database import get_database

load_dotenv()


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@aijewellery.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Email templates directory
TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__),
    "../templates/emails"
)

# Create templates directory if it doesn't exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)


# ============================================================
# SEND EMAIL (Using SendGrid)
# ============================================================

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
) -> bool:
    """
    Send email using SendGrid API.
    """
    if not SENDGRID_API_KEY:
        print("⚠️ SendGrid API key not configured. Email not sent.")
        print(f"📧 Email would be sent to: {to_email}")
        print(f"📧 Subject: {subject}")
        print(f"📧 Content preview: {html_content[:200] if html_content else 'No content'}...")
        return True

    try:
        # For testing without real email service
        if os.getenv("ENVIRONMENT") == "development":
            print(f"📧 Email would be sent to: {to_email}")
            print(f"📧 Subject: {subject}")
            print(f"📧 Content preview: {html_content[:200] if html_content else 'No content'}...")
            return True

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject,
                }
            ],
            "from": {"email": FROM_EMAIL},
            "content": [
                {
                    "type": "text/html",
                    "value": html_content,
                }
            ],
        }

        if text_content:
            data["content"].append({
                "type": "text/plain",
                "value": text_content,
            })

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data,
                headers=headers,
            )

        if response.status_code == 202:
            print(f"✅ Email sent successfully to {to_email}")
            return True
        else:
            print(f"❌ Email sending failed: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Email error: {str(e)}")
        return False


# ============================================================
# ORDER CONFIRMATION EMAIL
# ============================================================

async def send_order_confirmation_email(
    order_id: str,
) -> bool:
    """
    Send order confirmation email.
    """
    db = get_database()

    # Get order
    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id)
        }
    )

    if not order:
        print(f"❌ Order {order_id} not found")
        return False

    # Get user
    user = await db.users.find_one(
        {
            "_id": order["user"]
        }
    )

    if not user:
        print(f"❌ User not found for order {order_id}")
        return False

    # Prepare template data
    template_data = {
        "user_name": user.get("name", "Customer"),
        "order_number": order.get("order_number", f"ORD-{order_id[:8]}"),
        "order_date": order.get("created_at").strftime("%B %d, %Y") if order.get("created_at") else "N/A",
        "items": order.get("items", []),
        "shipping_address": order.get("shipping_address", {}),
        "items_price": order.get("items_price", 0),
        "tax_price": order.get("tax_price", 0),
        "shipping_price": order.get("shipping_price", 0),
        "total_price": order.get("total_price", 0),
        "payment_method": order.get("payment_method", "N/A"),
        "status": order.get("status", "pending"),
        "frontend_url": FRONTEND_URL,
        "year": datetime.utcnow().year,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Order Confirmation</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 5px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
            .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✨ Order Confirmation</h1>
            <p>Thank you for your purchase!</p>
        </div>
        <div class="content">
            <h2>Hi {template_data['user_name']},</h2>
            <p>We're excited to confirm your order!</p>
            <p><strong>Order Number:</strong> #{template_data['order_number']}</p>
            <p><strong>Order Date:</strong> {template_data['order_date']}</p>
            <p><strong>Total:</strong> ₹{template_data['total_price']:.2f}</p>
            <p><strong>Status:</strong> {template_data['status']}</p>
            <br>
            <a href="{template_data['frontend_url']}/orders" class="button">View Your Order</a>
        </div>
        <div class="footer">
            <p>© {template_data['year']} AI Jewellery Shop. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    return await send_email(
        user.get("email"),
        f"Order Confirmation - #{template_data['order_number']}",
        html_content,
        f"Thank you for your order! Your order number is {template_data['order_number']}",
    )


# ============================================================
# ORDER SHIPPED EMAIL
# ============================================================

async def send_order_shipped_email(
    order_id: str,
) -> bool:
    """
    Send order shipped notification.
    """
    db = get_database()

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id)
        }
    )

    if not order:
        print(f"❌ Order {order_id} not found")
        return False

    user = await db.users.find_one(
        {
            "_id": order["user"]
        }
    )

    if not user:
        print(f"❌ User not found for order {order_id}")
        return False

    template_data = {
        "user_name": user.get("name", "Customer"),
        "order_number": order.get("order_number", f"ORD-{order_id[:8]}"),
        "frontend_url": FRONTEND_URL,
        "year": datetime.utcnow().year,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Order Shipped</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 5px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
            .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚚 Order Shipped!</h1>
        </div>
        <div class="content">
            <h2>Hi {template_data['user_name']},</h2>
            <p>Your order has been shipped and is on its way to you!</p>
            <p><strong>Order Number:</strong> #{template_data['order_number']}</p>
            <br>
            <a href="{template_data['frontend_url']}/orders" class="button">Track Your Order</a>
        </div>
        <div class="footer">
            <p>© {template_data['year']} AI Jewellery Shop. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    return await send_email(
        user.get("email"),
        f"Your Order #{template_data['order_number']} Has Been Shipped",
        html_content,
    )


# ============================================================
# ORDER DELIVERED EMAIL
# ============================================================

async def send_order_delivered_email(
    order_id: str,
) -> bool:
    """
    Send order delivered notification.
    """
    db = get_database()

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id)
        }
    )

    if not order:
        print(f"❌ Order {order_id} not found")
        return False

    user = await db.users.find_one(
        {
            "_id": order["user"]
        }
    )

    if not user:
        print(f"❌ User not found for order {order_id}")
        return False

    template_data = {
        "user_name": user.get("name", "Customer"),
        "order_number": order.get("order_number", f"ORD-{order_id[:8]}"),
        "frontend_url": FRONTEND_URL,
        "year": datetime.utcnow().year,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Order Delivered</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 5px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
            .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✅ Order Delivered!</h1>
        </div>
        <div class="content">
            <h2>Hi {template_data['user_name']},</h2>
            <p>Your order has been successfully delivered!</p>
            <p><strong>Order Number:</strong> #{template_data['order_number']}</p>
            <p>We hope you love your new jewellery! 💎</p>
            <br>
            <a href="{template_data['frontend_url']}/orders" class="button">View Order</a>
        </div>
        <div class="footer">
            <p>© {template_data['year']} AI Jewellery Shop. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    return await send_email(
        user.get("email"),
        f"Your Order #{template_data['order_number']} Has Been Delivered",
        html_content,
    )


# ============================================================
# WELCOME EMAIL
# ============================================================

async def send_welcome_email(
    user_id: str,
) -> bool:
    """
    Send welcome email to new user.
    """
    db = get_database()

    user = await db.users.find_one(
        {
            "_id": ObjectId(user_id)
        }
    )

    if not user:
        print(f"❌ User {user_id} not found")
        return False

    template_data = {
        "user_name": user.get("name", "Customer"),
        "frontend_url": FRONTEND_URL,
        "year": datetime.utcnow().year,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Welcome to AI Jewellery Shop</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 5px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
            .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>👋 Welcome to AI Jewellery Shop!</h1>
        </div>
        <div class="content">
            <h2>Hi {template_data['user_name']},</h2>
            <p>Welcome to the future of jewellery shopping! We're thrilled to have you join our community.</p>
            <p>Discover AI-powered recommendations, virtual try-on, and our curated collection.</p>
            <br>
            <a href="{template_data['frontend_url']}" class="button">Start Shopping</a>
        </div>
        <div class="footer">
            <p>© {template_data['year']} AI Jewellery Shop. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    return await send_email(
        user.get("email"),
        f"Welcome to AI Jewellery Shop, {user.get('name')}!",
        html_content,
    )


# ============================================================
# PAYMENT VERIFIED EMAIL (Manual UPI)
# ============================================================

async def send_payment_verified_email(
    order_id: str,
) -> bool:
    """
    Send payment verified notification after admin approves UPI payment.
    """
    db = get_database()

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id)
        }
    )

    if not order:
        print(f"❌ Order {order_id} not found")
        return False

    user = await db.users.find_one(
        {
            "_id": order["user"]
        }
    )

    if not user:
        print(f"❌ User not found for order {order_id}")
        return False

    template_data = {
        "user_name": user.get("name", "Customer"),
        "order_number": order.get("order_number", f"ORD-{order_id[:8]}"),
        "total_price": order.get("total_price", 0),
        "upi_reference": order.get("upi_reference", "N/A"),
        "frontend_url": FRONTEND_URL,
        "year": datetime.utcnow().year,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Payment Verified</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 5px; }}
            .success-box {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0; border-radius: 4px; }}
            .button {{ display: inline-block; background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
            .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
            .details {{ background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✅ Payment Verified!</h1>
        </div>
        <div class="content">
            <h2>Hi {template_data['user_name']},</h2>
            <p>Great news! We've verified your UPI payment for the following order:</p>

            <div class="success-box">
                <strong>✅ Your order is now confirmed and being processed.</strong>
            </div>

            <div class="details">
                <p><strong>Order Number:</strong> #{template_data['order_number']}</p>
                <p><strong>Amount Paid:</strong> ₹{template_data['total_price']:.2f}</p>
                <p><strong>UPI Reference:</strong> {template_data['upi_reference']}</p>
                <p><strong>Status:</strong> Processing</p>
            </div>

            <p>Your order will be shipped soon. You'll receive tracking details via email once it's on the way.</p>
            <br>
            <a href="{template_data['frontend_url']}/orders" class="button">View Your Order</a>
        </div>
        <div class="footer">
            <p>Thank you for shopping with The Charm Boutique! 💎</p>
            <p>© {template_data['year']} AI Jewellery Shop. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    return await send_email(
        user.get("email"),
        f"✅ Payment Verified - Order #{template_data['order_number']}",
        html_content,
        f"Your payment for order {template_data['order_number']} has been verified. Your order is now confirmed!",
    )


# ============================================================
# PAYMENT REJECTED EMAIL (Manual UPI)
# ============================================================

async def send_payment_rejected_email(
    order_id: str,
    reason: str,
) -> bool:
    """
    Send payment rejected notification after admin rejects UPI payment.
    """
    db = get_database()

    order = await db.orders.find_one(
        {
            "_id": ObjectId(order_id)
        }
    )

    if not order:
        print(f"❌ Order {order_id} not found")
        return False

    user = await db.users.find_one(
        {
            "_id": order["user"]
        }
    )

    if not user:
        print(f"❌ User not found for order {order_id}")
        return False

    template_data = {
        "user_name": user.get("name", "Customer"),
        "order_number": order.get("order_number", f"ORD-{order_id[:8]}"),
        "total_price": order.get("total_price", 0),
        "reason": reason,
        "frontend_url": FRONTEND_URL,
        "year": datetime.utcnow().year,
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Payment Verification Failed</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 5px; }}
            .error-box {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; border-radius: 4px; }}
            .button {{ display: inline-block; background: #ef4444; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
            .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
            .details {{ background: white; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚠️ Payment Verification Failed</h1>
        </div>
        <div class="content">
            <h2>Hi {template_data['user_name']},</h2>
            <p>Unfortunately, we were unable to verify your payment for the following order:</p>

            <div class="error-box">
                <strong>Reason:</strong> {template_data['reason']}
            </div>

            <div class="details">
                <p><strong>Order Number:</strong> #{template_data['order_number']}</p>
                <p><strong>Amount:</strong> ₹{template_data['total_price']:.2f}</p>
                <p><strong>Status:</strong> Cancelled</p>
            </div>

            <p>If you believe this is a mistake, please contact us with a clear payment screenshot and we'll resolve it quickly.</p>

            <p><strong>What happens next?</strong></p>
            <ul>
                <li>If payment was NOT deducted: you can place a new order.</li>
                <li>If payment WAS deducted: contact us immediately with your UPI transaction ID.</li>
            </ul>

            <br>
            <a href="{template_data['frontend_url']}/orders" class="button">View Your Orders</a>
        </div>
        <div class="footer">
            <p>Need help? Reply to this email and we'll assist you.</p>
            <p>© {template_data['year']} AI Jewellery Shop. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    return await send_email(
        user.get("email"),
        f"⚠️ Payment Verification Failed - Order #{template_data['order_number']}",
        html_content,
        f"Your payment for order {template_data['order_number']} could not be verified. Reason: {reason}",
    )


# ============================================================
# ALIAS FOR BACKWARD COMPATIBILITY
# ============================================================

# Alias for notification_service to use
send_order_confirmation = send_order_confirmation_email