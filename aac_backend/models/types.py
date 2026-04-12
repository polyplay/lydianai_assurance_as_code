from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


def id_column(prefix: str) -> Mapped[str]:
    return mapped_column(String(64), primary_key=True, default=lambda: new_id(prefix))
