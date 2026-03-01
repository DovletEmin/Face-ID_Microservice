"""Auth service tests."""

import pytest
from app.auth.jwt_handler import JWTHandler


class TestJWTHandler:
    """Tests for JWT token handling."""

    def setup_method(self):
        self.handler = JWTHandler()

    def test_create_and_verify_token(self):
        """Token creation and verification roundtrip."""
        token = self.handler.create_access_token("user-123", "testuser")
        payload = self.handler.verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "user-123"
        assert payload["username"] == "testuser"
        assert payload["auth_method"] == "face_id"

    def test_invalid_token_rejected(self):
        """Invalid token returns None."""
        payload = self.handler.verify_token("not.a.valid.token")
        assert payload is None

    def test_tampered_token_rejected(self):
        """Tampered token returns None."""
        token = self.handler.create_access_token("user-123", "testuser")
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        payload = self.handler.verify_token(tampered)
        assert payload is None
