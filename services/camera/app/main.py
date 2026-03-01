"""Camera Service — Main application entry point.

Manages the Intel RealSense D415 camera lifecycle
and exposes REST + WebSocket APIs for frame access.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.camera.realsense import RealSenseCamera
from app.camera.depth import DepthProcessor
from app.camera.stream import StreamManager
from app.api.routes import router as api_router
from app.api.websocket import router as ws_router
from app.config import get_settings

# Module-level instances (accessed by route handlers)
camera: RealSenseCamera = RealSenseCamera()
depth_processor: DepthProcessor = DepthProcessor()
stream_manager: StreamManager = StreamManager(camera, depth_processor)

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start/stop camera on app startup/shutdown."""
    logger.info("Starting Camera Service...")
    success = camera.start()
    if success:
        logger.info("Camera initialized successfully.")
    else:
        logger.warning(
            "Camera failed to initialize. "
            "Running in simulation mode."
        )
    yield
    logger.info("Shutting down Camera Service...")
    await stream_manager.stop_streaming()
    camera.stop()
    logger.info("Camera Service stopped.")


app = FastAPI(
    title="Face ID — Camera Service",
    description="Intel RealSense D415 camera streaming and depth capture",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend and gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_router)
app.include_router(ws_router)
