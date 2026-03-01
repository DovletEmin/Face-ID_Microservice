"""API Gateway schemas."""

from pydantic import BaseModel
from typing import Optional


class GatewayHealth(BaseModel):
    status: str = "ok"
    service: str = "api-gateway"
    services: dict = {}
