from typing import Dict, List, Set
import asyncio
from fastapi import WebSocket


class ConnectionManager:
    """
    WebSocket connection manager for real-time notifications.
    """

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str = None,
    ):
        """
        Accept WebSocket connection.
        """
        await websocket.accept()

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

        # Add to general connections
        if "all" not in self.active_connections:
            self.active_connections["all"] = set()
        self.active_connections["all"].add(websocket)

    def disconnect(
        self,
        websocket: WebSocket,
        user_id: str = None,
    ):
        """
        Remove WebSocket connection.
        """
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        if "all" in self.active_connections:
            self.active_connections["all"].discard(websocket)

    async def send_to_user(
        self,
        user_id: str,
        message: dict,
    ):
        """
        Send message to a specific user.
        """
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    pass

    async def broadcast(
        self,
        message: dict,
    ):
        """
        Broadcast message to all connected clients.
        """
        if "all" in self.active_connections:
            for websocket in self.active_connections["all"]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    pass


# Global connection manager instance
manager = ConnectionManager()