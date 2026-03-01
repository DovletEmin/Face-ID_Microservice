"""API Gateway configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    service_name: str = "api-gateway"
    debug: bool = False

    # Gateway
    api_gateway_host: str = "0.0.0.0"
    api_gateway_port: int = 8000

    # Backend services
    camera_service_host: str = "camera-service"
    camera_service_port: int = 8001
    face_service_host: str = "face-service"
    face_service_port: int = 8002
    auth_service_host: str = "auth-service"
    auth_service_port: int = 8003

    # JWT (for token validation at gateway level)
    jwt_secret_key: str = "change_me_to_a_random_secret_key_at_least_32_chars"
    jwt_algorithm: str = "HS256"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    log_level: str = "INFO"

    @property
    def camera_service_url(self) -> str:
        return f"http://{self.camera_service_host}:{self.camera_service_port}"

    @property
    def face_service_url(self) -> str:
        return f"http://{self.face_service_host}:{self.face_service_port}"

    @property
    def auth_service_url(self) -> str:
        return f"http://{self.auth_service_host}:{self.auth_service_port}"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
