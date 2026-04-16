export type Driver = {
  name: string;
  direction: "up" | "down" | "flat";
  impact: "high" | "medium" | "low";
  evidence: string;
};

export type TrustPassport = {
  confidence: string;
  completeness: string;
  freshness: string;
  sourceAgreement: string;
  underreportingRisk: string;
  action: string;
};

export type TractRiskPackage = {
  regionId: string;
  regionName: string;
  city: string;
  riskLevel: string;
  baselineScore: number;
  mlScore: number;
  scores: {
    overall: number;
    violent: number;
    property: number;
  };
  drivers: Driver[];
  trustPassport: TrustPassport;
  liveDisagreement: {
    status: string;
    summary: string;
    delta: number;
  };
  whatChanged: {
    summary: string;
    topChanges: string[];
  };
};

export type LiveEvent = {
  id: string;
  title: string;
  status: string;
  confidence: string;
  sourceType: string;
  occurredAt: string;
  summary: string;
};

export type PersonaDecision = {
  persona: string;
  decision: string;
  headline: string;
  nextStep: string;
  caveat: string;
  abstain: boolean;
};

export const tractRiskPackage: TractRiskPackage = {
  regionId: "17031010100",
  regionName: "Near North Side Example Tract",
  city: "Chicago",
  riskLevel: "elevated",
  baselineScore: 72,
  mlScore: 76,
  scores: {
    overall: 76,
    violent: 61,
    property: 82,
  },
  drivers: [
    {
      name: "Recent property crime density",
      direction: "up",
      impact: "high",
      evidence: "Historical property incidents rose over the prior 30-day window.",
    },
    {
      name: "Nightlife corridor pressure",
      direction: "up",
      impact: "medium",
      evidence: "High venue density and late-hour activity raise short-term volatility.",
    },
    {
      name: "Transit access",
      direction: "flat",
      impact: "low",
      evidence: "Transit remains a stable contextual factor in this tract.",
    },
  ],
  trustPassport: {
    confidence: "moderate",
    completeness: "high",
    freshness: "recent",
    sourceAgreement: "mixed",
    underreportingRisk: "moderate",
    action: "manual review",
  },
  liveDisagreement: {
    status: "watch",
    summary:
      "Live signals suggest short-term pressure above the verified historical baseline.",
    delta: 8,
  },
  whatChanged: {
    summary:
      "The score moved up because short-term property pressure and corridor activity increased.",
    topChanges: [
      "Property crime density is the largest positive driver.",
      "One official bulletin elevated short-term concern.",
      "Neighboring tracts are also trending upward this week.",
    ],
  },
};

export const liveEvents: LiveEvent[] = [
  {
    id: "evt-001",
    title: "Official bulletin referencing commercial burglary pattern",
    status: "verified",
    confidence: "high",
    sourceType: "official_bulletin",
    occurredAt: "2026-04-03T08:15:00Z",
    summary: "Pattern bulletin overlaps the current tract and two adjacent tracts.",
  },
  {
    id: "evt-002",
    title: "Local alert about late-night vehicle break-ins",
    status: "reported",
    confidence: "medium",
    sourceType: "public_alert",
    occurredAt: "2026-04-03T05:40:00Z",
    summary: "Signal is location-resolved but still awaiting stronger corroboration.",
  },
];

export const insurerDecision: PersonaDecision = {
  persona: "insurer",
  decision: "manual review",
  headline: "Review pricing and underwriting notes before approval.",
  nextStep:
    "Route this tract to manual underwriting review and request supplemental safeguards.",
  caveat:
    "Confidence is moderate because verified history and live signals are not fully aligned.",
  abstain: false,
};

