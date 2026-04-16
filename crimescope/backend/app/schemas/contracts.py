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
