"""
main.py
Application Entrypoint for AI-Based Electronic Failure Prediction Platform.
Combines FastAPI REST Engine with Static Dashboard and Telemetry Gateway.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.database import initialize_database
from api.routes import router as api_router

STATIC_DIR = os.path.join(ROOT_DIR, "static")
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        initialize_database()
    except Exception:
        pass
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
elif os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "service": "EcoPredict AI", "engine": "LightGBM + TreeSHAP + SQLite"}


@app.get("/")
def serve_dashboard():
    for folder in (STATIC_DIR, PUBLIC_DIR):
        index_file = os.path.join(folder, "index.html")
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
