"""
main.py
Application Entrypoint for AI-Based Electronic Failure Prediction Platform.
Combines FastAPI REST Engine with Static Dashboard and Telemetry Gateway.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from core.database import initialize_database
from api.routes import router as api_router

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    initialize_database()
    yield


app = FastAPI(
    title="EcoPredict AI - Fleet Failure Prediction & Circular Maintenance",
    description="Green Computing & Sustainable AI Platform for Electronic Asset Failure Prevention (Studi Kasus 23)",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development (Live Server port 5500, Vite, React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

# Mount static folder for CSS, JS, and HTML UI
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "service": "EcoPredict AI", "engine": "LightGBM + TreeSHAP + SQLite"}


@app.get("/")
def serve_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": "EcoPredict AI API is running. Access API documentation at /docs",
        "api_endpoints": "/api/v1/overview"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port)
