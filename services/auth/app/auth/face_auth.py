"""Face authentication orchestrator.

Coordinates between Camera Service and Face Processing Service
to perform end-to-end face authentication.
"""

import logging
from typing import Optional

import httpx

from app.config import get_settings
from app.auth.jwt_handler import JWTHandler

logger = logging.getLogger(__name__)


class FaceAuthenticator:
    """Orchestrates face-based authentication flow."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._jwt = JWTHandler()

    async def authenticate_with_camera(self) -> dict:
        """Full authentication flow:
        1. Capture frame from camera service
        2. Send to face service for authentication
        3. Generate JWT if successful

        Returns:
            Authentication result dict.
        """
        # Step 1: Capture frame from camera
        frame_data = await self._capture_frame()
        if frame_data is None:
            return {
                "authenticated": False,
                "message": "Failed to capture camera frame.",
            }

        # Step 2: Authenticate face
        return await self.authenticate_with_frame(
            color_frame_b64=frame_data["color"],
            depth_data_b64=frame_data.get("depth"),
            depth_shape=frame_data.get("depth_shape"),
        )

    async def authenticate_with_frame(
        self,
        color_frame_b64: str,
        depth_data_b64: Optional[str] = None,
        depth_shape: Optional[list] = None,
    ) -> dict:
        """Authenticate using a pre-captured frame.

        Args:
            color_frame_b64: Base64-encoded JPEG color frame.
            depth_data_b64: Base64-encoded depth data.
            depth_shape: Shape of depth frame.

        Returns:
            Authentication result with JWT token if successful.
        """
        payload = {"color_frame_b64": color_frame_b64}
        if depth_data_b64:
            payload["depth_data_b64"] = depth_data_b64
        if depth_shape:
            payload["depth_shape"] = depth_shape

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._settings.face_service_url}/api/v1/face/authenticate",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

        except httpx.HTTPError as e:
            logger.error(f"Face service connection error: {e}")
            return {
                "authenticated": False,
                "message": "Face processing service unavailable.",
            }

        if not result.get("authenticated"):
            return result

        # Generate JWT token for authenticated user
        user_id = result["user_id"]
        username = result["username"]

        token = self._jwt.create_access_token(user_id, username)

        return {
            "authenticated": True,
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self._jwt.token_expire_minutes * 60,
            "user_id": user_id,
            "username": username,
            "confidence": result.get("confidence", 0.0),
            "anti_spoof": result.get("anti_spoof"),
            "message": "Authentication successful.",
        }

    async def enroll_with_camera(
        self, username: str, full_name: Optional[str] = None
    ) -> dict:
        """Enroll a new face using camera capture.

        Args:
            username: Username for enrollment.
            full_name: Optional full name.

        Returns:
            Enrollment result dict.
        """
        frame_data = await self._capture_frame()
        if frame_data is None:
            return {
                "success": False,
                "message": "Failed to capture camera frame.",
            }

        return await self.enroll_with_frame(
            username=username,
            full_name=full_name,
            color_frame_b64=frame_data["color"],
            depth_data_b64=frame_data.get("depth"),
            depth_shape=frame_data.get("depth_shape"),
        )

    async def enroll_with_frame(
        self,
        username: str,
        color_frame_b64: str,
        full_name: Optional[str] = None,
        depth_data_b64: Optional[str] = None,
        depth_shape: Optional[list] = None,
    ) -> dict:
        """Enroll using a pre-captured frame."""
        payload = {
            "username": username,
            "full_name": full_name,
            "color_frame_b64": color_frame_b64,
        }
        if depth_data_b64:
            payload["depth_data_b64"] = depth_data_b64
        if depth_shape:
            payload["depth_shape"] = depth_shape

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._settings.face_service_url}/api/v1/face/enroll",
                    json=payload,
                )
                if response.status_code >= 500:
                    logger.error(
                        f"Face service enrollment HTTP {response.status_code}: {response.text[:200]}"
                    )
                    return {"success": False, "message": "Face processing service error."}
                try:
                    return response.json()
                except Exception as json_err:
                    logger.error(f"Face service enrollment non-JSON response: {json_err}")
                    return {"success": False, "message": "Face processing service returned invalid response."}

        except httpx.HTTPError as e:
            logger.error(f"Face service enrollment error: {e}")
            return {
                "success": False,
                "message": "Face processing service unavailable.",
            }

    async def _capture_frame(self) -> Optional[dict]:
        """Capture a frame from the camera service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._settings.camera_service_url}/api/v1/camera/capture"
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Camera service error: {e}")
            return None
