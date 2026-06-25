import asyncio
import os
from contextlib import suppress

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.ai.predict import predict_latest
from backend.api.database import get_db
from backend.api.load_balancing import router as load_balancing_router
from backend.api.predictions import router as predictions_router
from backend.api.routes import dashboard, faults, nodes, telemetry
from backend.api.telemetry_simulator import (
    router as telemetry_simulator_router,
    start_telemetry_simulator,
)


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


@app.on_event("startup")
async def startup_event():
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
            await asyncio.to_thread(predict_latest)
            print("V.E.N.U.S AI prediction cycle completed")
        except Exception as error:
            print(f"V.E.N.U.S AI prediction cycle failed: {error}")

        await asyncio.sleep(30)