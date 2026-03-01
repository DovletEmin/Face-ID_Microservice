"""Auth service Pydantic schemas."""

from pydantic import BaseModel
from typing import Optional


class FaceLoginRequest(BaseModel):
    """Request to authenticate via face.

    The auth service will call the camera service to capture a frame,
    then the face service to authenticate.
    """
    pass  # No fields needed — camera captures automatically


class FaceLoginWithFrameRequest(BaseModel):
    """Authentication request with pre-captured frame data."""
    color_frame_b64: str
    depth_data_b64: Optional[str] = None
    depth_shape: Optional[list] = None


class TokenResponse(BaseModel):
    """JWT token response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str


class TokenValidation(BaseModel):
    """Token validation result."""
    valid: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    message: str = ""


class EnrollRequest(BaseModel):
    """Face enrollment request (proxy to face service)."""
    username: str
    full_name: Optional[str] = None


class EnrollWithFrameRequest(BaseModel):
    """Enrollment with pre-captured frame."""
    username: str
    full_name: Optional[str] = None
    color_frame_b64: str
    depth_data_b64: Optional[str] = None
    depth_shape: Optional[list] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "auth-service"
