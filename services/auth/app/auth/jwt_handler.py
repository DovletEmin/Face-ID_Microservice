"""JWT token creation and validation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)


class JWTHandler:
    """Handles JWT token generation and verification."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def create_access_token(
        self,
        user_id: str,
        username: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a signed JWT access token.

        Args:
            user_id: User UUID string.
            username: Username.
            expires_delta: Custom expiration time.

        Returns:
            Encoded JWT token string.
        """
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=self._settings.jwt_access_token_expire_minutes
            )

        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": user_id,
            "username": username,
            "iat": now,
            "exp": expire,
            "type": "access",
            "auth_method": "face_id",
        }

        token = jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

        logger.debug(f"Token created for user {username}, expires {expire}")
        return token

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string.

        Returns:
            Decoded payload dict, or None if invalid.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )

            user_id = payload.get("sub")
            username = payload.get("username")

            if user_id is None:
                logger.warning("Token missing 'sub' claim.")
                return None

            return {
                "user_id": user_id,
                "username": username,
                "exp": payload.get("exp"),
                "auth_method": payload.get("auth_method"),
            }

        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None

    @property
    def token_expire_minutes(self) -> int:
        return self._settings.jwt_access_token_expire_minutes
