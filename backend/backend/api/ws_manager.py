import json

from fastapi import WebSocket


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Tracks connected clients, accepts new connections,
    removes disconnected clients, and broadcasts JSON
    events safely without crashing on stale connections.
    """

    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._active:
            self._active.remove(websocket)

    async def broadcast(self, event_type: str, data: object) -> None:
        """
        Broadcasts a JSON event to all connected clients.

        Stale / already-closed connections are silently removed
        so the backend never crashes on a dead WebSocket.
        """
        message = json.dumps({"event": event_type, "data": data})
        dead: list[WebSocket] = []

        for connection in list(self._active):
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)

        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()
