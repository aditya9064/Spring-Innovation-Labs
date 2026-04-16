"""SQLAlchemy model for human challenge mode records."""
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(60), nullable=False)
    region_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    challenger_name: Mapped[str] = mapped_column(String(200), nullable=False)
    challenge_type: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="")
    proposed_adjustment: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
