from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )

    violation_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    person_track_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    snapshot_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    annotated_snapshot_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50), default="open", nullable=False
    )
