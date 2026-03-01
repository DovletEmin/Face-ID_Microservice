"""Auth service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    service_name: str = "auth-service"
    debug: bool = False

    # JWT
    jwt_secret_key: str = "change_me_to_a_random_secret_key_at_least_32_chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Face service
    face_service_host: str = "face-service"
    face_service_port: int = 8002

    # Camera service
    camera_service_host: str = "camera-service"
    camera_service_port: int = 8001

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    log_level: str = "INFO"

    @property
    def face_service_url(self) -> str:
        return f"http://{self.face_service_host}:{self.face_service_port}"

    @property
    def camera_service_url(self) -> str:
        return f"http://{self.camera_service_host}:{self.camera_service_port}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
