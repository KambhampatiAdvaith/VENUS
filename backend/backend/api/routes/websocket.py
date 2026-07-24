from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.ws_manager import manager


router = APIRouter()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time V.E.N.U.S dashboard updates.

    Clients connect here and receive JSON events broadcast by the backend
    after key operations (telemetry ingestion, AI predictions, fault alerts,
    load balancing changes).

    Event schema:
        {"event": "<type>", "data": { ... }}

    Event types:
        - "telemetry"      : new telemetry cycle written to the database
        - "prediction"     : AI prediction cycle completed
        - "fault"          : new fault alert created
        - "load_balancing" : recommendation / approval / rejection updated
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
