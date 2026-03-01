"""Face processing service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Face processing service settings."""

    service_name: str = "face-service"
    debug: bool = False

    # Face detection
    face_detection_confidence: float = 0.7
    face_recognition_threshold: float = 0.6
    face_embedding_size: int = 512

    # Anti-spoofing
    anti_spoof_threshold: float = 0.5

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "face_id"
    postgres_user: str = "face_id_user"
    postgres_password: str = "change_me_in_production"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # Camera service
    camera_service_host: str = "camera-service"
    camera_service_port: int = 8001

    # Model paths
    model_cache_dir: str = "/app/models"

    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
