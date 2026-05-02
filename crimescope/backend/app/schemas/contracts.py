from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Driver(BaseModel):
    name: str
    direction: Literal["up", "down", "flat"]
    impact: Literal["high", "medium", "low"]
    evidence: str


class TrustPassport(BaseModel):
    confidence: str
    completeness: str
    freshness: str
    sourceAgreement: str
    underreportingRisk: str
    action: str


class ScoreBreakdown(BaseModel):
    overall: int
    violent: int
    property: int


class LiveDisagreement(BaseModel):
    status: str
    summary: str
    delta: int


class WhatChanged(BaseModel):
    summary: str
    topChanges: list[str]


class TractRiskPackage(BaseModel):
    regionId: str
    regionType: str
    regionName: str
    city: str
    timeHorizonDays: int
    riskLevel: str
    baselineScore: int
    mlScore: int
    scores: ScoreBreakdown
    drivers: list[Driver]
    trustPassport: TrustPassport
    liveDisagreement: LiveDisagreement
    whatChanged: WhatChanged
    updatedAt: datetime


class LiveBanner(BaseModel):
    status: str
    headline: str
    summary: str
    updatedAt: datetime


class LiveEvent(BaseModel):
    id: str
    title: str
    status: str
    confidence: str
    sourceType: str
    occurredAt: datetime
    resolvedRegionId: str
    lat: float
    lng: float
    summary: str


class LiveEventPackage(BaseModel):
    regionId: str
    banner: LiveBanner
    events: list[LiveEvent]


class PersonaDecisionPackage(BaseModel):
    persona: str
    regionId: str
    decision: str
    headline: str
    nextStep: str
    caveat: str
    abstain: bool


class ReportSummaryPackage(BaseModel):
    regionId: str
    title: str
    executiveSummary: str
    riskDrivers: list[str]
    trustNotes: list[str]
    compareSummary: str
    challengeState: str


class CompareDriver(BaseModel):
    name: str
    direction: Literal["up", "down", "flat"]
    impact: float
    summary: str


class CompareRecommendation(BaseModel):
    persona: str
    label: str
    nextStep: str
    caveat: str
    reviewRequired: bool


class CompareRegionSnapshot(BaseModel):
    regionId: str
    regionName: str
    city: str
    geographyType: str
    score: int
    baselineScore: int
    mlScore: int
    confidence: float
    completeness: float
    freshnessHours: int
    trustStatus: str
    underreportingRisk: str
    topDrivers: list[CompareDriver]
    recommendation: CompareRecommendation
    liveDisagreement: LiveDisagreement


class CompareResponse(BaseModel):
    left: CompareRegionSnapshot
    right: CompareRegionSnapshot
    summary: str


# ---------------------------------------------------------------------------
# Trend / forecast (real near-term risk projection)
# ---------------------------------------------------------------------------


class TrendPoint(BaseModel):
    date: str  # ISO date (YYYY-MM-DD)
    value: float


class TrendForecastPoint(BaseModel):
    date: str
    value: float
    lo: float
    hi: float


class RegionTrend(BaseModel):
    regionId: str
    regionName: str
    metric: Literal["risk_score", "incident_rate"]
    horizonDays: int
    history: list[TrendPoint]
    forecast: list[TrendForecastPoint]
    method: str  # honest description of the forecast method
    calibrationNote: str  # caveat about the forecast quality
    trendDirection: Literal["rising", "falling", "stable"]
    next30dExpected: float
    next30dLo: float
    next30dHi: float


# ---------------------------------------------------------------------------
# Crime pattern breakdown (category-level)
# ---------------------------------------------------------------------------


class BreakdownCategory(BaseModel):
    category: str
    label: str
    count30d: int
    share: float  # 0..1
    trendDirection: Literal["rising", "falling", "stable"]
    trendPct: float  # e.g. +12.5 means 12.5% higher than prior window


class RegionBreakdown(BaseModel):
    regionId: str
    regionName: str
    windowDays: int
    total30d: int
    categories: list[BreakdownCategory]
    note: str  # provenance note


# ---------------------------------------------------------------------------
# Pricing guidance (insurer + real-estate personas)
# ---------------------------------------------------------------------------


class PricingDriver(BaseModel):
    name: str
    contributionPct: float  # signed; +12.5 means this driver adds 12.5% to the multiplier
    evidence: str


class PricingQuote(BaseModel):
    regionId: str
    regionName: str
    persona: Literal["insurer", "real_estate"]
    basePremium: float
    suggestedPremium: float
    riskMultiplier: float  # suggested / base
    band: Literal["preferred", "standard", "surcharge", "high_risk", "decline_recommended"]
    drivers: list[PricingDriver]
    confidence: float  # 0..1
    methodology: str
    alpha: float
    beta: float
    riskFactor: float
    tierLoading: float
    caveats: list[str]
