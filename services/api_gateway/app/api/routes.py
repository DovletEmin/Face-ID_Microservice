"""API Gateway — REST routes that proxy requests to backend services."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.middleware.auth import verify_jwt_token, require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()


# ==================== Health ====================


@router.get("/api/v1/health")
async def gateway_health():
    """Overall system health check — pings all services."""
    services = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in [
            ("camera", f"{settings.camera_service_url}/api/v1/camera/health"),
            ("face", f"{settings.face_service_url}/api/v1/face/health"),
            ("auth", f"{settings.auth_service_url}/api/v1/auth/health"),
        ]:
            try:
                resp = await client.get(url)
                services[name] = "ok" if resp.status_code == 200 else "error"
            except Exception:
                services[name] = "unavailable"

    all_ok = all(s == "ok" for s in services.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "service": "api-gateway",
        "services": services,
    }


# ==================== Auth (public) ====================


@router.post("/api/v1/auth/login/face")
async def proxy_login_face():
    """Proxy face login to auth service (server-side camera capture)."""
    return await _proxy_post(
        f"{settings.auth_service_url}/api/v1/auth/login/face",
        body=None,
    )


@router.post("/api/v1/auth/login/face/frame")
async def proxy_login_face_frame(request: Request):
    """Proxy face login with frame to auth service."""
    body = await request.json()
    return await _proxy_post(
        f"{settings.auth_service_url}/api/v1/auth/login/face/frame",
        body=body,
    )


@router.post("/api/v1/auth/enroll")
async def proxy_enroll(request: Request):
    """Proxy face enrollment to auth service."""
    body = await request.json()
    return await _proxy_post(
        f"{settings.auth_service_url}/api/v1/auth/enroll",
        body=body,
    )


@router.post("/api/v1/auth/enroll/frame")
async def proxy_enroll_frame(request: Request):
    """Proxy face enrollment with frame to auth service."""
    body = await request.json()
    return await _proxy_post(
        f"{settings.auth_service_url}/api/v1/auth/enroll/frame",
        body=body,
    )


@router.post("/api/v1/auth/verify")
async def proxy_verify_token(request: Request):
    """Proxy token verification."""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    return await _proxy_post(
        f"{settings.auth_service_url}/api/v1/auth/verify",
        body=None,
        headers=headers,
    )


@router.post("/api/v1/auth/logout")
async def proxy_logout(request: Request):
    """Proxy logout."""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    return await _proxy_post(
        f"{settings.auth_service_url}/api/v1/auth/logout",
        body=None,
        headers=headers,
    )


# ==================== Camera (authenticated) ====================


@router.get("/api/v1/camera/info")
async def proxy_camera_info(
    request: Request,
    auth: dict = Depends(verify_jwt_token),
):
    """Get camera info (requires authentication)."""
    _ = require_auth(auth)
    return await _proxy_get(
        f"{settings.camera_service_url}/api/v1/camera/info"
    )


@router.post("/api/v1/camera/capture")
async def proxy_camera_capture(
    request: Request,
    auth: dict = Depends(verify_jwt_token),
):
    """Capture camera frame (requires authentication)."""
    _ = require_auth(auth)
    return await _proxy_post(
        f"{settings.camera_service_url}/api/v1/camera/capture",
        body=None,
    )


# ==================== Face (authenticated) ====================


@router.get("/api/v1/face/users")
async def proxy_list_users(
    request: Request,
    auth: dict = Depends(verify_jwt_token),
):
    """List enrolled users (requires authentication)."""
    _ = require_auth(auth)
    return await _proxy_get(
        f"{settings.face_service_url}/api/v1/face/users"
    )


# ==================== Proxy helpers ====================


async def _proxy_get(url: str, headers: dict = None) -> JSONResponse:
    """Forward a GET request to a backend service."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers or {})
            return JSONResponse(
                content=resp.json(),
                status_code=resp.status_code,
            )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable.")
    except Exception as e:
        logger.error(f"Proxy GET error: {e}")
        raise HTTPException(status_code=502, detail="Bad gateway.")


async def _proxy_post(
    url: str,
    body: dict = None,
    headers: dict = None,
) -> JSONResponse:
    """Forward a POST request to a backend service."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body, headers=headers or {})
            try:
                content = resp.json()
            except Exception:
                content = {"detail": resp.text[:500] or "Empty response from service"}
            return JSONResponse(content=content, status_code=resp.status_code)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable.")
    except Exception as e:
        logger.error(f"Proxy POST error: {e}")
        raise HTTPException(status_code=502, detail="Bad gateway.")
