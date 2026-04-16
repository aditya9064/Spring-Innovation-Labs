"""SQLAlchemy models for tract-level data: scores, boundaries, ACS demographics, pipeline stats."""
from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TractScore(Base):
    __tablename__ = "tract_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tract_geoid: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    month_start: Mapped[str] = mapped_column(String(40), nullable=True)
    predicted_next_30d: Mapped[float] = mapped_column(Float, default=0)
    predicted_violent_30d: Mapped[float] = mapped_column(Float, default=0)
    predicted_property_30d: Mapped[float] = mapped_column(Float, default=0)
    baseline_predicted: Mapped[float] = mapped_column(Float, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    violent_score: Mapped[float] = mapped_column(Float, default=0)
    property_score: Mapped[float] = mapped_column(Float, default=0)
    risk_tier: Mapped[str] = mapped_column(String(20), default="Unknown")
    model_vs_baseline: Mapped[float] = mapped_column(Float, default=0)
    trend_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    incident_count: Mapped[float] = mapped_column(Float, default=0)
    y_incidents_12m: Mapped[int] = mapped_column(Integer, default=0)
    y_violent_12m: Mapped[int] = mapped_column(Integer, default=0)
    y_property_12m: Mapped[int] = mapped_column(Integer, default=0)
    lag_1m_count: Mapped[float] = mapped_column(Float, default=0)
    rolling_mean_3m: Mapped[float] = mapped_column(Float, default=0)
    rolling_mean_12m: Mapped[float] = mapped_column(Float, default=0)
    violent_ratio: Mapped[float] = mapped_column(Float, default=0)
    violent_ratio_6m: Mapped[float] = mapped_column(Float, default=0)
    top_drivers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_pop_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_hh_income_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poverty_rate_acs: Mapped[float | None] = mapped_column(Float, nullable=True)
    housing_units_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    namelsad: Mapped[str | None] = mapped_column("NAMELSAD", String(100), nullable=True)
    scored_at: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(20), nullable=True)


class TractBoundary(Base):
    __tablename__ = "tract_boundaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tract_geoid: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    namelsad: Mapped[str | None] = mapped_column("NAMELSAD", String(100), nullable=True)
    wkt: Mapped[str | None] = mapped_column(Text, nullable=True)
    geom: Mapped[str | None] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    aland: Mapped[int | None] = mapped_column("ALAND", BigInteger, nullable=True)


class TractACS(Base):
    __tablename__ = "tract_acs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tract_geoid: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    total_pop_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_hh_income_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poverty_count_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poverty_rate_acs: Mapped[float | None] = mapped_column(Float, nullable=True)
    housing_units_acs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acs_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PipelineStats(Base):
    __tablename__ = "pipeline_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    n_tracts: Mapped[int] = mapped_column(Integer, default=0)
    n_months: Mapped[int] = mapped_column(Integer, default=0)
    data_start: Mapped[str | None] = mapped_column(String(60), nullable=True)
    data_end: Mapped[str | None] = mapped_column(String(60), nullable=True)
