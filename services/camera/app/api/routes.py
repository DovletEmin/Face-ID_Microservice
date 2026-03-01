"""Camera service REST API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import CameraInfo, CameraStatus, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/camera", tags=["camera"])


def _get_camera():
    """Get camera instance from app state (set during startup)."""
    from app.main import camera, depth_processor, stream_manager

    return camera, depth_processor, stream_manager


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Camera service health check."""
    camera, _, _ = _get_camera()
    return HealthResponse(
        status="ok",
        service="camera-service",
        camera=(
            CameraStatus.CONNECTED
            if camera.is_running
            else CameraStatus.DISCONNECTED
        ),
    )


@router.get("/info", response_model=CameraInfo)
async def camera_info():
    """Get camera hardware information and status."""
    camera, _, _ = _get_camera()
    from app.config import get_settings

    settings = get_settings()

    return CameraInfo(
        status=(
            CameraStatus.CONNECTED
            if camera.is_running
            else CameraStatus.DISCONNECTED
        ),
        serial_number=camera.serial_number,
        firmware_version=camera.firmware_version,
        frame_width=settings.camera_frame_width,
        frame_height=settings.camera_frame_height,
        fps=settings.camera_fps,
        depth_enabled=settings.camera_depth_enabled,
    )


@router.post("/capture")
async def capture_frame():
    """Capture a single frame with color and depth data.

    Used for face enrollment and authentication.
    Returns base64-encoded frame data.
    """
    _, _, stream = _get_camera()
    frame_data = await stream.capture_single_frame()
    if frame_data is None:
        raise HTTPException(
            status_code=503,
            detail="Failed to capture frame. Camera may be disconnected.",
        )
    return frame_data


@router.get("/stream/status")
async def stream_status():
    """Get current streaming status."""
    _, _, stream = _get_camera()
    return {
        "is_streaming": stream.is_streaming,
        "connected_clients": stream.client_count,
    }
