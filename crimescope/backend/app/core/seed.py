"""Seed PostgreSQL database from JSON files exported by Databricks.

Usage:
    cd crimescope/backend
    python -m app.core.seed
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.database import Base, engine, async_session_factory
from app.models.tract import TractScore, TractBoundary, TractACS, PipelineStats
from app.models.audit import AuditEntry  # noqa: F401 — ensure table is registered
from app.models.challenge import Challenge  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

BATCH_SIZE = 200


async def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning("File not found: %s", path)
        return []
    with open(path) as f:
        return json.load(f)


async def _seed_scores(session):
    rows = await _load_json(DATA_DIR / "tract_risk_scores.json")
    if not rows:
        return
    logger.info("Seeding %d tract scores...", len(rows))

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        objects = []
        for r in batch:
            objects.append(TractScore(
                tract_geoid=r["tract_geoid"],
                month_start=r.get("month_start"),
                predicted_next_30d=r.get("predicted_next_30d", 0),
                predicted_violent_30d=r.get("predicted_violent_30d", 0),
                predicted_property_30d=r.get("predicted_property_30d", 0),
                baseline_predicted=r.get("baseline_predicted", 0),
                risk_score=r.get("risk_score", 0),
                violent_score=r.get("violent_score", 0),
                property_score=r.get("property_score", 0),
                risk_tier=r.get("risk_tier", "Unknown"),
                model_vs_baseline=r.get("model_vs_baseline", 0),
                trend_direction=r.get("trend_direction"),
                incident_count=r.get("incident_count", 0),
                y_incidents_12m=r.get("y_incidents_12m", 0),
                y_violent_12m=r.get("y_violent_12m", 0),
                y_property_12m=r.get("y_property_12m", 0),
                lag_1m_count=r.get("lag_1m_count", 0),
                rolling_mean_3m=r.get("rolling_mean_3m", 0),
                rolling_mean_12m=r.get("rolling_mean_12m", 0),
                violent_ratio=r.get("violent_ratio", 0),
                violent_ratio_6m=r.get("violent_ratio_6m", 0),
                top_drivers_json=r.get("top_drivers_json"),
                total_pop_acs=r.get("total_pop_acs"),
                median_hh_income_acs=r.get("median_hh_income_acs"),
                poverty_rate_acs=r.get("poverty_rate_acs"),
                housing_units_acs=r.get("housing_units_acs"),
                namelsad=r.get("NAMELSAD"),
                scored_at=r.get("scored_at"),
                model_name=r.get("model_name"),
                model_version=r.get("model_version"),
            ))
        session.add_all(objects)
        await session.flush()

    logger.info("Scores seeded.")


async def _seed_boundaries(session):
    rows = await _load_json(DATA_DIR / "cook_tract_boundaries.json")
    if not rows:
        return
    logger.info("Seeding %d tract boundaries...", len(rows))

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        objects = []
        for r in batch:
            wkt_str = r.get("wkt", "")
            geom_expr = None
            if wkt_str:
                geom_expr = text(f"ST_GeomFromText(:wkt, 4326)")

            obj = TractBoundary(
                tract_geoid=r["tract_geoid"],
                namelsad=r.get("NAMELSAD"),
                wkt=wkt_str,
                aland=r.get("ALAND"),
            )
            objects.append(obj)
        session.add_all(objects)
        await session.flush()

        if wkt_str:
            for obj in objects:
                if obj.wkt:
                    await session.execute(
                        text(
                            "UPDATE tract_boundaries SET geom = ST_GeomFromText(:wkt, 4326) WHERE id = :id"
                        ),
                        {"wkt": obj.wkt, "id": obj.id},
                    )

    logger.info("Boundaries seeded.")


async def _seed_acs(session):
    rows = await _load_json(DATA_DIR / "tract_acs_population.json")
    if not rows:
        return
    logger.info("Seeding %d ACS records...", len(rows))

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        objects = []
        for r in batch:
            objects.append(TractACS(
                tract_geoid=r["tract_geoid"],
                total_pop_acs=r.get("total_pop_acs"),
                median_hh_income_acs=r.get("median_hh_income_acs"),
                poverty_count_acs=r.get("poverty_count_acs"),
                poverty_rate_acs=r.get("poverty_rate_acs"),
                housing_units_acs=r.get("housing_units_acs"),
                acs_year=r.get("acs_year"),
            ))
        session.add_all(objects)
        await session.flush()

    logger.info("ACS seeded.")


async def _seed_stats(session):
    rows = await _load_json(DATA_DIR / "pipeline_stats.json")
    if not rows:
        return
    logger.info("Seeding pipeline stats...")

    for r in rows:
        session.add(PipelineStats(
            total_rows=r.get("total_rows", 0),
            n_tracts=r.get("n_tracts", 0),
            n_months=r.get("n_months", 0),
            data_start=r.get("data_start"),
            data_end=r.get("data_end"),
        ))

    logger.info("Stats seeded.")


async def main():
    logger.info("Creating tables...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Checking if data already seeded...")
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM tract_scores"))
        count = result.scalar()
        if count and count > 0:
            logger.info("Database already has %d scores. Skipping seed. Use --force to re-seed.", count)
            if "--force" not in sys.argv:
                await engine.dispose()
                return
            logger.info("Force flag detected. Truncating tables...")
            await session.execute(text("TRUNCATE tract_scores, tract_boundaries, tract_acs, pipeline_stats CASCADE"))
            await session.commit()

    async with async_session_factory() as session:
        async with session.begin():
            await _seed_scores(session)
            await _seed_boundaries(session)
            await _seed_acs(session)
            await _seed_stats(session)

    logger.info("Seed complete.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
