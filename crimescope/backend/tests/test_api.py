"""Basic API integration tests for CrimeScope backend."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_scores():
    r = client.get("/api/regions/scores")
    assert r.status_code == 200
    data = r.json()
    assert "tracts" in data
    assert isinstance(data["tracts"], list)


def test_tiers():
    r = client.get("/api/regions/tiers")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for tier in data:
        assert "tier" in tier
        assert "count" in tier
        assert "pct" in tier


def test_score_single():
    scores_r = client.get("/api/regions/scores")
    tracts = scores_r.json()["tracts"]
    if tracts:
        geoid = tracts[0]["tract_geoid"]
        r = client.get(f"/api/regions/score?region_id={geoid}")
        assert r.status_code == 200


def test_score_not_found():
    r = client.get("/api/regions/score?region_id=00000000000")
    assert r.status_code == 404


def test_blind_spots():
    r = client.get("/api/regions/blind-spots")
    assert r.status_code == 200
    assert "blind_spots" in r.json()


def test_geojson():
    r = client.get("/api/map/geojson")
    assert r.status_code == 200
    geo = r.json()
    assert geo["type"] == "FeatureCollection"
    assert isinstance(geo["features"], list)


def test_live_banner():
    r = client.get("/api/live/banner")
    assert r.status_code == 200
    d = r.json()
    assert "headline" in d
    assert "status" in d


def test_live_feed():
    r = client.get("/api/live/feed")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_report_summary():
    scores_r = client.get("/api/regions/scores")
    tracts = scores_r.json()["tracts"]
    if tracts:
        geoid = tracts[0]["tract_geoid"]
        r = client.get(f"/api/reports/summary?region_id={geoid}")
        assert r.status_code == 200
        d = r.json()
        assert "executiveSummary" in d
        assert "riskDrivers" in d


def test_persona_decision():
    scores_r = client.get("/api/regions/scores")
    tracts = scores_r.json()["tracts"]
    if tracts:
        geoid = tracts[0]["tract_geoid"]
        r = client.get(f"/api/reports/persona-decision?region_id={geoid}")
        assert r.status_code == 200
        assert "decision" in r.json()


def test_compare():
    scores_r = client.get("/api/regions/scores")
    tracts = scores_r.json()["tracts"]
    if len(tracts) >= 2:
        r = client.get(
            f"/api/compare?left_region_id={tracts[0]['tract_geoid']}"
            f"&right_region_id={tracts[1]['tract_geoid']}"
        )
        assert r.status_code == 200
        d = r.json()
        assert "left" in d
        assert "right" in d
        assert "summary" in d


def test_simulator_interventions():
    r = client.get("/api/simulator/interventions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_simulator_run():
    scores_r = client.get("/api/regions/scores")
    tracts = scores_r.json()["tracts"]
    if tracts:
        r = client.post(
            "/api/simulator/run",
            json={
                "region_id": tracts[0]["tract_geoid"],
                "interventions": [{"id": "increase_patrols", "intensity": 1.0}],
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["simulated_score"] <= d["original_score"]
        assert d["delta"] <= 0


def test_audit_crud():
    r = client.get("/api/audit")
    assert r.status_code == 200

    create_r = client.post(
        "/api/audit",
        json={
            "region_id": "17031839100",
            "persona": "insurer",
            "decision": "accept",
            "rationale": "Low risk tract",
            "risk_score": 25.0,
            "risk_tier": "Low",
        },
    )
    assert create_r.status_code == 201
    assert create_r.json()["decision"] == "accept"

    stats_r = client.get("/api/audit/stats")
    assert stats_r.status_code == 200
    assert stats_r.json()["total_decisions"] >= 1


def test_challenge_crud():
    r = client.get("/api/challenge")
    assert r.status_code == 200

    create_r = client.post(
        "/api/challenge",
        json={
            "region_id": "17031839100",
            "challenger_name": "Test User",
            "challenge_type": "score_too_high",
            "evidence": "Local knowledge suggests lower actual risk.",
        },
    )
    assert create_r.status_code == 201
    cid = create_r.json()["id"]
    assert create_r.json()["status"] == "pending"

    review_r = client.put(
        f"/api/challenge/{cid}",
        json={"status": "accepted", "reviewer_notes": "Valid evidence."},
    )
    assert review_r.status_code == 200
    assert review_r.json()["status"] == "accepted"

    stats_r = client.get("/api/challenge/stats")
    assert stats_r.status_code == 200
    assert stats_r.json()["total_challenges"] >= 1
