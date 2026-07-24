import asyncio
from datetime import date, datetime
from typing import Any

from backend.api.ws_manager import manager


_event_loop: asyncio.AbstractEventLoop | None = None


def configure_live_broadcast_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


def serialize_live_data(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {key: serialize_live_data(item) for key, item in value.items()}

    if isinstance(value, list):
        return [serialize_live_data(item) for item in value]

    return value


def broadcast_from_thread(event_type: str, data: dict[str, Any]) -> None:
    if _event_loop is None or not _event_loop.is_running():
        return

    asyncio.run_coroutine_threadsafe(
        manager.broadcast(event_type, serialize_live_data(data)),
        _event_loop,
    )


def broadcast_kafka_telemetry(data: dict[str, Any]) -> None:
    broadcast_from_thread(
        "telemetry",
        {
            "source": "kafka",
            "substation": data.get("substation"),
            "timestamp": data.get("timestamp"),
            "edge_anomaly": data.get("edge_anomaly", False),
            "edge_anomaly_score": data.get("edge_anomaly_score"),
            "edge_model": data.get("edge_model"),
        },
    )


def broadcast_fault(data: dict[str, Any]) -> None:
    broadcast_from_thread("fault", data)
