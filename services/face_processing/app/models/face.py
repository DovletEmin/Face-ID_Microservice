"""SQLAlchemy database models and session management."""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import Boolean, Column, DateTime, Float, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class User(Base):
    """Users table model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    enrollments = relationship("FaceEnrollment", back_populates="user")
    auth_logs = relationship("AuthLog", back_populates="user")


class FaceEnrollment(Base):
    """Face enrollments table — stores face embeddings + depth signatures."""

    __tablename__ = "face_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # embedding stored as pgvector via raw SQL (SQLAlchemy pgvector support)
    depth_signature = Column(JSONB, default={})
    quality_score = Column(Float, default=0.0)
    is_primary = Column(Boolean, default=False)
    enrolled_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="enrollments")


class AuthLog(Base):
    """Authentication log entries."""

    __tablename__ = "auth_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    success = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=True)
    depth_verified = Column(Boolean, default=False)
    anti_spoof_score = Column(Float, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="auth_logs")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
