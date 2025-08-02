"""
Base model classes with common functionality.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base for all SQLAlchemy models."""
    pass


class BaseModel(Base):
    """Base model class with common functionality."""
    
    __abstract__ = True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update model instance from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )