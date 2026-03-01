"""Auth service REST API routes."""

import logging

from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.auth.jwt_handler import JWTHandler
from app.auth.face_auth import FaceAuthenticator
from app.schemas import (
    FaceLoginRequest,
    FaceLoginWithFrameRequest,
    TokenResponse,
    TokenValidation,
    EnrollRequest,
    EnrollWithFrameRequest,
    HealthResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

jwt_handler = JWTHandler()
face_auth = FaceAuthenticator()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", service="auth-service")


@router.post("/login/face")
async def login_face():
    """Authenticate using face via camera capture.

    The server captures a frame from the RealSense camera
    and processes it for face authentication.
    Returns a JWT token on success.
    """
    result = await face_auth.authenticate_with_camera()

    if not result.get("authenticated"):
        raise HTTPException(
            status_code=401,
            detail=result.get("message", "Authentication failed."),
        )

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        user_id=result["user_id"],
        username=result["username"],
    )


@router.post("/login/face/frame")
async def login_face_with_frame(request: FaceLoginWithFrameRequest):
    """Authenticate using a pre-captured frame from the frontend.

    Use this when the frontend captures frames via WebSocket
    and sends them for authentication.
    """
    result = await face_auth.authenticate_with_frame(
        color_frame_b64=request.color_frame_b64,
        depth_data_b64=request.depth_data_b64,
        depth_shape=request.depth_shape,
    )

    if not result.get("authenticated"):
        raise HTTPException(
            status_code=401,
            detail=result.get("message", "Authentication failed."),
        )

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        user_id=result["user_id"],
        username=result["username"],
    )


@router.post("/enroll")
async def enroll_face(request: EnrollRequest):
    """Enroll a new face via camera capture."""
    result = await face_auth.enroll_with_camera(
        username=request.username,
        full_name=request.full_name,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Enrollment failed."),
        )

    return result


@router.post("/enroll/frame")
async def enroll_face_with_frame(request: EnrollWithFrameRequest):
    """Enroll a new face using a pre-captured frame."""
    result = await face_auth.enroll_with_frame(
        username=request.username,
        full_name=request.full_name,
        color_frame_b64=request.color_frame_b64,
        depth_data_b64=request.depth_data_b64,
        depth_shape=request.depth_shape,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Enrollment failed."),
        )

    return result


@router.post("/verify", response_model=TokenValidation)
async def verify_token(
    authorization: Optional[str] = Header(None),
):
    """Verify a JWT access token."""
    if not authorization:
        return TokenValidation(valid=False, message="No token provided.")

    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return TokenValidation(valid=False, message="Invalid token format.")

    token = parts[1]
    payload = jwt_handler.verify_token(token)

    if payload is None:
        return TokenValidation(valid=False, message="Invalid or expired token.")

    return TokenValidation(
        valid=True,
        user_id=payload["user_id"],
        username=payload["username"],
        message="Token is valid.",
    )


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None),
):
    """Logout — invalidate the current token.

    In a stateless JWT setup, the frontend simply discards the token.
    For extra security, we could blacklist tokens in Redis.
    """
    # Future: add token to Redis blacklist
    return {"message": "Logged out successfully."}
