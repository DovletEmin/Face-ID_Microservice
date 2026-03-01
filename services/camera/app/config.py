"""Camera service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Camera service settings loaded from environment."""

    # Service
    service_name: str = "camera-service"
    debug: bool = False

    # Camera
    camera_frame_width: int = 640
    camera_frame_height: int = 480
    camera_fps: int = 30
    camera_depth_enabled: bool = True

    # Depth processing
    depth_min_distance: float = 0.1  # meters
    depth_max_distance: float = 1.5  # meters (face should be within 1.5m)

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    # JPEG quality for streaming
    stream_jpeg_quality: int = 80

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
