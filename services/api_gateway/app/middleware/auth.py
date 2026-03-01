"""JWT authentication middleware for the API Gateway."""

import logging
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def verify_jwt_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[dict]:
    """Verify JWT token from Authorization header.

    Returns decoded payload or None if no token.
    Raises HTTPException for invalid tokens.
    """
    # Try to get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        )


def require_auth(payload: Optional[dict]) -> dict:
    """Require a valid JWT token. Use as a route dependency."""
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login with Face ID.",
        )
    return payload
