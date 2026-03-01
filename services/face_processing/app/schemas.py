"""Pydantic schemas for Face Processing service."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class FaceDetection(BaseModel):
    """Detected face bounding box and landmarks."""
    bbox: List[int] = Field(..., description="[x1, y1, x2, y2]")
    confidence: float
    landmarks: Optional[List[List[float]]] = None


class AntiSpoofResult(BaseModel):
    """Anti-spoofing analysis result."""
    is_real: bool
    confidence: float
    depth_verified: bool
    method: str = "depth_analysis"


class FaceEmbeddingResult(BaseModel):
    """Face embedding extraction result."""
    embedding: List[float]
    quality_score: float
    detection: FaceDetection


class MatchResult(BaseModel):
    """Face matching result."""
    matched: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    similarity: float
    anti_spoof: AntiSpoofResult


class EnrollRequest(BaseModel):
    """Face enrollment request."""
    username: str
    full_name: Optional[str] = None
    color_frame_b64: str = Field(..., description="Base64-encoded JPEG color frame")
    depth_data_b64: Optional[str] = Field(None, description="Base64-encoded depth data")
    depth_shape: Optional[List[int]] = None


class EnrollResponse(BaseModel):
    """Face enrollment response."""
    success: bool
    user_id: Optional[str] = None
    message: str
    quality_score: float = 0.0


class AuthenticateRequest(BaseModel):
    """Face authentication request."""
    color_frame_b64: str
    depth_data_b64: Optional[str] = None
    depth_shape: Optional[List[int]] = None


class AuthenticateResponse(BaseModel):
    """Face authentication response."""
    authenticated: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    confidence: float = 0.0
    anti_spoof: Optional[AntiSpoofResult] = None
    message: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "face-service"
    model_loaded: bool = False
