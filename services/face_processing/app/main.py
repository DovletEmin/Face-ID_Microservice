"""Face Processing Service — Main application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — preload ML models on startup."""
    logger.info("Starting Face Processing Service...")
    logger.info("Loading face detection & recognition models...")

    # Pre-load InsightFace model (takes a few seconds on first load)
    from app.processing.detector import FaceDetector

    det = FaceDetector()
    # Trigger lazy loading
    try:
        import numpy as np

        dummy = np.zeros((112, 112, 3), dtype=np.uint8)
        det.detect_faces(dummy)
        logger.info("Face models loaded successfully.")
    except Exception as e:
        logger.warning(f"Model pre-load failed (will retry on first request): {e}")

    yield

    logger.info("Face Processing Service stopped.")


app = FastAPI(
    title="Face ID — Face Processing Service",
    description="Face detection, embedding, matching, and anti-spoofing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
