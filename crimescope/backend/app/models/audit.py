"""SQLAlchemy model for the decision audit trail."""
from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(60), nullable=False)
    region_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    persona: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="")
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    risk_tier: Mapped[str] = mapped_column(String(20), default="Unknown")
    overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
