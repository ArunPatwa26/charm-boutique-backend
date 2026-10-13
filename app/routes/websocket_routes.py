from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi_socketio import SocketManager
import json

from app.services.websocket_manager import manager
from app.middleware.auth import JWTBearer
from app.controllers.auth_controller import get_current_user


async def websocket_endpoint(
    websocket: WebSocket,
    token: str = None,
):
    """
    WebSocket endpoint for real-time notifications.
    """
    user_id = None

    # Authenticate user from token
    if token:
        try:
            user = await get_current_user(token)
            user_id = user.get("id")
        except Exception:
            pass

    await manager.connect(websocket, user_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "message": "Connected to AI Jewellery Shop WebSocket",
        })

        while True:
            # Receive messages (keep connection alive)
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # Echo back for debugging
                await websocket.send_json({
                    "type": "echo",
                    "data": json.loads(data) if data else {},
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket, user_id)