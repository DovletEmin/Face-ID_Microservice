"""Pydantic schemas for Camera service API."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CameraStatus(str, Enum):
    """Camera connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"


class CameraInfo(BaseModel):
    """Camera hardware information."""
    status: CameraStatus
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    frame_width: int
    frame_height: int
    fps: int
    depth_enabled: bool


class FrameCapture(BaseModel):
    """Single frame capture result."""
    timestamp: float
    has_color: bool = True
    has_depth: bool = True
    face_region: Optional[dict] = None


class DepthData(BaseModel):
    """Depth map metadata for a captured frame."""
    min_depth: float = Field(..., description="Minimum depth in meters")
    max_depth: float = Field(..., description="Maximum depth in meters")
    mean_depth: float = Field(..., description="Mean depth in meters")
    valid_pixels_ratio: float = Field(..., description="Ratio of valid depth pixels")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "camera-service"
    camera: CameraStatus = CameraStatus.DISCONNECTED
