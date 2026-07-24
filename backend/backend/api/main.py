import asyncio
import os
import threading
from contextlib import suppress

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.ai.predict import predict_latest
from backend.api.database import get_db, ensure_telemetry_timestamp_columns
from backend.api.live_broadcast import (
    broadcast_fault,
    broadcast_kafka_telemetry,
    configure_live_broadcast_loop,
)
from backend.api.load_balancing import router as load_balancing_router
from backend.api.predictions import router as predictions_router
from backend.api.routes import dashboard, faults, nodes, telemetry, websocket
from backend.api.ws_manager import manager
from backend.api.telemetry_simulator import (
    router as telemetry_simulator_router,
    start_telemetry_simulator,
)
from backend.kafka.fault_consumer import start_fault_consumer
from backend.kafka.telemetry_consumer import start_telemetry_consumer


load_dotenv()


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def is_enabled(env_var_name: str, default: str = "false") -> bool:
    return os.getenv(env_var_name, default).strip().lower() in {"true", "1", "yes"}


def get_allowed_origins() -> list[str]:
    origins = [
        FRONTEND_URL.strip(),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    return [origin for origin in dict.fromkeys(origins) if origin]


def start_daemon_thread(name: str, target, *args) -> threading.Thread:
    thread = threading.Thread(
        name=name,
        target=target,
        args=args,
        daemon=True,
    )
    thread.start()
    return thread


app = FastAPI(
    title="V.E.N.U.S. API",
    description="Backend APIs for Volt Edge Network Utility System",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(telemetry.router)
app.include_router(faults.router)
app.include_router(dashboard.router)
app.include_router(nodes.router)
app.include_router(predictions_router)
app.include_router(load_balancing_router)
app.include_router(telemetry_simulator_router)
app.include_router(websocket.router)


@app.on_event("startup")
async def startup_event():
    configure_live_broadcast_loop(asyncio.get_running_loop())
    ensure_telemetry_timestamp_columns()

    if is_enabled("ENABLE_STARTUP_TELEMETRY_SIMULATOR"):
        print("[telemetry-simulator] Startup simulator enabled.")
        start_telemetry_simulator()
    else:
        print("[telemetry-simulator] Startup simulator disabled for edge-cloud demo.")

    if is_enabled("ENABLE_AI_PREDICTION_LOOP"):
        app.state.ai_prediction_task = asyncio.create_task(run_ai_prediction_loop())
        print("[ai-prediction-loop] Started.")
    else:
        app.state.ai_prediction_task = None
        print("[ai-prediction-loop] Disabled by default. Run predictions manually.")

    if is_enabled("ENABLE_KAFKA_TELEMETRY_CONSUMER"):
        app.state.kafka_telemetry_thread = start_daemon_thread(
            "venus-kafka-telemetry-consumer",
            start_telemetry_consumer,
            broadcast_kafka_telemetry,
        )
        print("[kafka-telemetry-consumer] Started with live WebSocket broadcast.")
    else:
        app.state.kafka_telemetry_thread = None
        print("[kafka-telemetry-consumer] Disabled by default.")

    if is_enabled("ENABLE_KAFKA_FAULT_CONSUMER"):
        app.state.kafka_fault_thread = start_daemon_thread(
            "venus-kafka-fault-consumer",
            start_fault_consumer,
            broadcast_fault,
        )
        print("[kafka-fault-consumer] Started with live WebSocket broadcast.")
    else:
        app.state.kafka_fault_thread = None
        print("[kafka-fault-consumer] Disabled by default.")


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "ai_prediction_task", None)

    if task is None:
        return

    task.cancel()

    with suppress(asyncio.CancelledError):
        await task


@app.get("/")
def root():
    return {
        "project": "V.E.N.U.S.",
        "name": "Volt Edge Network Utility System",
        "status": "running",
    }


@app.get("/health")
def health_check():
    db_generator = get_db()

    try:
        db = next(db_generator)
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception as error:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(error),
        }
    finally:
        db_generator.close()


async def run_ai_prediction_loop():
    while True:
        try:
            fault_events = []
            await asyncio.to_thread(predict_latest, fault_events.append)
            for fault_event in fault_events:
                await manager.broadcast("fault", fault_event)
            print("V.E.N.U.S AI prediction cycle completed")
            await manager.broadcast(
                "prediction",
                {"message": "V.E.N.U.S AI prediction cycle completed"},
            )
        except Exception as error:
            print(f"V.E.N.U.S AI prediction cycle failed: {error}")

        await asyncio.sleep(30)