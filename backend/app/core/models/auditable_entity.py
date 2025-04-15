from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel

from app.core.models.entity import Entity

class AuditableEntity(Entity,SQLModel):
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

