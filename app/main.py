from datetime import datetime

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.config.database import (
    connect_to_mongo,
    close_mongo_connection,
    get_database,
)

from app.routes import (
    auth_routes,
    category_routes,
    product_routes,
    cart_routes,
    order_routes,
    ai_routes,
    admin_routes,
    wishlist_routes,
)

from app.utils.error_handler import global_exception_handler

from app.services.websocket_manager import manager


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Jewellery Shop API",
    description="Backend for AI-powered jewellery e-commerce platform",
    version="1.0.0",
)


# ============================================================
# CORS MIDDLEWARE
# IMPORTANT: Add this before routes
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://the-charm-boutique.vercel.app/",
        "https://the-charm-boutique.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

app.add_exception_handler(
    Exception,
    global_exception_handler,
)


# ============================================================
# STARTUP EVENT
# ============================================================

@app.on_event("startup")
async def startup_event():

    await connect_to_mongo()

    print("🚀 AI Jewellery Shop API started")
    print("📦 MongoDB connected")


# ============================================================
# SHUTDOWN EVENT
# ============================================================

@app.on_event("shutdown")
async def shutdown_event():

    await close_mongo_connection()

    print("👋 Server shutting down...")


# ============================================================
# AUTH ROUTES
# ============================================================

app.include_router(
    auth_routes.router,
    prefix="/api/auth",
    tags=["Authentication"],
)


# ============================================================
# CATEGORY ROUTES
# ============================================================

app.include_router(
    category_routes.router,
    prefix="/api/categories",
    tags=["Categories"],
)


# ============================================================
# PRODUCT ROUTES
# ============================================================

app.include_router(
    product_routes.router,
    prefix="/api/products",
    tags=["Products"],
)


# ============================================================
# CART ROUTES
# ============================================================

app.include_router(
    cart_routes.router,
    prefix="/api/cart",
    tags=["Cart"],
)


# ============================================================
# ORDER ROUTES
# (Includes manual UPI payment proof endpoints)
# ============================================================

app.include_router(
    order_routes.router,
    prefix="/api/orders",
    tags=["Orders"],
)


# ============================================================
# AI ROUTES
# ============================================================

app.include_router(
    ai_routes.router,
    prefix="/api/ai",
    tags=["AI Features"],
)


# ============================================================
# ADMIN ROUTES
# ============================================================

app.include_router(
    admin_routes.router,
    prefix="/api/admin",
    tags=["Admin"],
)


# ============================================================
# WISHLIST ROUTES
# ============================================================

app.include_router(
    wishlist_routes.router,
    prefix="/api/wishlist",
    tags=["Wishlist"],
)


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    token = websocket.query_params.get("token")

    user_id = None

    if token:

        try:

            from app.controllers.auth_controller import get_current_user

            user = await get_current_user(token)

            user_id = user.get("id")

        except Exception as error:

            print(
                f"WebSocket authentication failed: {error}"
            )

    await manager.connect(
        websocket,
        user_id,
    )

    try:

        await websocket.send_json(
            {
                "type": "connection",
                "status": "connected",
                "user_id": user_id,
                "message": "Connected to AI Jewellery Shop WebSocket",
            }
        )

        while True:

            data = await websocket.receive_text()

            if data == "ping":

                await websocket.send_text(
                    "pong"
                )

            else:

                await websocket.send_json(
                    {
                        "type": "echo",
                        "data": data,
                    }
                )

    except Exception as error:

        print(
            f"WebSocket error: {error}"
        )

        manager.disconnect(
            websocket,
            user_id,
        )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "message": "Welcome to AI Jewellery Shop API",
        "status": "Server is running",
        "version": "1.0.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health_check():

    try:

        db = get_database()

        await db.command("ping")

        db_status = "Connected"

    except Exception as error:

        db_status = f"Error: {str(error)}"

    return {
        "status": "OK",
        "message": "Server is healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }