import asyncio
import os

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


app = FastAPI(
    title="V.E.N.U.S. API",
    description="Backend APIs for Volt Edge Network Utility System",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
def startup_event():
    enable_startup_simulator = os.getenv(
        "ENABLE_STARTUP_TELEMETRY_SIMULATOR",
        "false",
    ).lower() == "true"

    if enable_startup_simulator:
        print("[telemetry-simulator] Startup simulator enabled.")
        start_telemetry_simulator()
    else:
        print("[telemetry-simulator] Startup simulator disabled for edge-cloud demo.")


@app.get("/")
def root():
    return {
        "project": "V.E.N.U.S.",
        "name": "Volt Edge Network Utility System",
        "status": "running",
    }


@app.get("/health")
def health_check():
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()

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


async def run_ai_prediction_loop():
    while True:
        try:
            await asyncio.to_thread(predict_latest)
            print("V.E.N.U.S AI prediction cycle completed")
        except Exception as error:
            print(f"V.E.N.U.S AI prediction cycle failed: {error}")

        await asyncio.sleep(30)