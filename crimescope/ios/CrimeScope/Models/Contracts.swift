import Foundation
import CoreLocation

enum RiskTier: String, Codable, CaseIterable, Hashable, Sendable {
    case critical = "Critical"
    case high = "High"
    case elevated = "Elevated"
    case moderate = "Moderate"
    case low = "Low"

    var sortOrder: Int {
        switch self {
        case .critical: return 0
        case .high: return 1
        case .elevated: return 2
        case .moderate: return 3
        case .low: return 4
        }
    }
}

enum Persona: String, Codable, CaseIterable, Identifiable, Sendable {
    case insurance
    case publicSafety = "public_safety"
    case logistics
    case real_estate
    case civic
    case journalist

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .insurance: return "Insurance"
        case .publicSafety: return "Public Safety"
        case .logistics: return "Logistics"
        case .real_estate: return "Real Estate"
        case .civic: return "Civic"
        case .journalist: return "Journalist"
        }
    }

    var caption: String {
        switch self {
        case .insurance: return "Underwriting & coverage decisions"
        case .publicSafety: return "Patrols, deployment, response"
        case .logistics: return "Routing, delivery windows"
        case .real_estate: return "Property risk & appraisal"
        case .civic: return "Equity & community signals"
        case .journalist: return "Investigation & verification"
        }
    }
}

struct TractScore: Codable, Identifiable, Hashable, Sendable {
    let geoid: String
    let name: String
    let tier: RiskTier
    let score: Double
    let baselineScore: Double
    let mlScore: Double
    let violentScore: Double
    let propertyScore: Double
    let centroid: Coordinate
    let confidence: Double
    let lastUpdated: Date
    /// Predicted incidents in the next 30 days (from the ML pipeline export). 0 when unknown.
    let predictedNext30d: Double
    /// Persisted trend label from the pipeline. nil when unknown.
    let trendDirection: TrendDirection?

    var id: String { geoid }
}

enum TrendDirection: String, Codable, Hashable, Sendable {
    case rising, falling, stable
}

struct Coordinate: Codable, Hashable, Sendable {
    let latitude: Double
    let longitude: Double

    var clLocation: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

struct TrustPassport: Codable, Hashable, Sendable {
    let confidence: Double
    let completeness: Double
    let freshness: Double
    let sourceAgreement: Double
    let underreportingRisk: Double
    let recommendedAction: String
    let summary: String
}

struct Driver: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let label: String
    let direction: Direction
    let impact: Double
    let evidence: String
    let category: String

    enum Direction: String, Codable, Hashable, Sendable {
        case up, down, neutral
    }
}

struct WhatChangedItem: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let label: String
    let delta: Double
    let detail: String
}

struct PersonaDecision: Codable, Hashable, Sendable {
    let persona: Persona
    let recommendation: String
    let confidence: Double
    let nextSteps: [String]
    let caveats: [String]
}

struct TractRiskPackage: Codable, Hashable, Sendable {
    let geoid: String
    let name: String
    let riskLevel: String
    let scores: Scores
    let baselineScore: Double
    let mlScore: Double
    let trustPassport: TrustPassport
    let drivers: [Driver]
    let whatChanged: [WhatChangedItem]
    let personaDecisions: [PersonaDecision]
    let liveDisagreement: LiveDisagreement
    let lastUpdated: Date

    struct Scores: Codable, Hashable, Sendable {
        let overall: Double
        let violent: Double
        let property: Double
    }
}

struct LiveDisagreement: Codable, Hashable, Sendable {
    enum Status: String, Codable, Hashable, Sendable {
        case aligned, watch, divergent
    }
    let status: Status
    let summary: String
    /// Signed delta in score points (ML − baseline).
    let delta: Int
}

struct LiveEvent: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let geoid: String
    let regionName: String
    let category: String
    let source: Source
    let status: Status
    let confidence: Double
    let summary: String
    let occurredAt: Date

    enum Source: String, Codable, Hashable, Sendable {
        case dispatch_911 = "911"
        case fire
        case sensor
        case social
        case news
        case crowdsource
    }

    enum Status: String, Codable, Hashable, Sendable {
        case verified
        case pending
        case unverified
    }
}

struct CompareSnapshot: Codable, Hashable, Sendable {
    let geoid: String
    let name: String
    let tier: RiskTier
    let score: Double
    let baselineScore: Double
    let mlScore: Double
    let trust: TrustPassport
    let topDrivers: [Driver]
    let liveDelta: Double
    let recommendation: String
}

struct ReportSummary: Codable, Hashable, Sendable {
    let geoid: String
    let name: String
    let tier: RiskTier
    let executiveSummary: String
    let riskNarrative: String
    let trustNotes: String
    let drivers: [Driver]
    let peerCompare: [PeerEntry]
    let challenges: [String]
    let generatedAt: Date

    struct PeerEntry: Codable, Hashable, Sendable {
        let geoid: String
        let name: String
        let score: Double
        let tier: RiskTier
    }
}

struct Intervention: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let label: String
    let description: String
    let unit: String
    let minValue: Double
    let maxValue: Double
    let defaultValue: Double
    let estimatedImpact: Double
}

struct SimulationResult: Codable, Hashable, Sendable {
    let baselineScore: Double
    let simulatedScore: Double
    let projectedTier: RiskTier
    let narrative: String
    let breakdown: [Breakdown]

    struct Breakdown: Codable, Identifiable, Hashable, Sendable {
        let id: String
        let label: String
        let delta: Double
    }
}

struct AuditRecord: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let geoid: String
    let regionName: String
    let persona: Persona
    let riskScore: Double
    let riskTier: RiskTier
    let decision: String
    let rationale: String
    let overrodeMl: Bool
    let createdAt: Date
}

struct ChallengeRecord: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let geoid: String
    let regionName: String
    let challengerName: String
    let challengeType: ChallengeType
    let evidence: String
    let proposedAdjustment: Double
    let status: Status
    let createdAt: Date

    enum ChallengeType: String, Codable, CaseIterable, Hashable, Sendable {
        case data, model, decision, scope

        var displayName: String { rawValue.capitalized }
    }

    enum Status: String, Codable, CaseIterable, Hashable, Sendable {
        case pending, approved, rejected, in_review

        var displayName: String {
            switch self {
            case .pending: return "Pending"
            case .approved: return "Approved"
            case .rejected: return "Rejected"
            case .in_review: return "In Review"
            }
        }
    }
}

struct ChatMessage: Identifiable, Hashable, Sendable {
    let id: UUID
    let role: Role
    let text: String
    let createdAt: Date

    enum Role: String, Hashable, Sendable {
        case user, assistant
    }
}

struct TractPolygon: Identifiable, Hashable, Sendable {
    let geoid: String
    let coordinates: [Coordinate]
    let tier: RiskTier
    let score: Double

    var id: String { geoid }
}

// MARK: - Trend / forecast

struct TrendPoint: Codable, Hashable, Sendable, Identifiable {
    let date: String
    let value: Double
    var id: String { date }
}

struct TrendForecastPoint: Codable, Hashable, Sendable, Identifiable {
    let date: String
    let value: Double
    let lo: Double
    let hi: Double
    var id: String { date }
}

struct RegionTrend: Codable, Hashable, Sendable {
    let regionId: String
    let regionName: String
    let metric: String
    let horizonDays: Int
    let history: [TrendPoint]
    let forecast: [TrendForecastPoint]
    let method: String
    let calibrationNote: String
    let trendDirection: TrendDirection
    let next30dExpected: Double
    let next30dLo: Double
    let next30dHi: Double
}

// MARK: - Crime pattern breakdown

struct BreakdownCategory: Codable, Hashable, Sendable, Identifiable {
    let category: String
    let label: String
    let count30d: Int
    let share: Double
    let trendDirection: TrendDirection
    let trendPct: Double
    var id: String { category }
}

struct RegionBreakdown: Codable, Hashable, Sendable {
    let regionId: String
    let regionName: String
    let windowDays: Int
    let total30d: Int
    let categories: [BreakdownCategory]
    let note: String
}

// MARK: - Pricing guidance

enum PricingPersonaKey: String, Codable, Hashable, Sendable, CaseIterable, Identifiable {
    case insurer
    case real_estate
    var id: String { rawValue }
    var displayName: String { self == .insurer ? "Insurer" : "Real Estate" }
    var defaultBase: Double { self == .insurer ? 1200 : 100 }
    var baseLabel: String { self == .insurer ? "Base premium" : "Risk loading on $100" }
}

enum PricingBand: String, Codable, Hashable, Sendable {
    case preferred
    case standard
    case surcharge
    case high_risk
    case decline_recommended

    var displayName: String {
        switch self {
        case .preferred: return "Preferred"
        case .standard: return "Standard"
        case .surcharge: return "Surcharge"
        case .high_risk: return "High Risk"
        case .decline_recommended: return "Decline / Review"
        }
    }
}

struct PricingDriver: Codable, Hashable, Sendable, Identifiable {
    let name: String
    let contributionPct: Double
    let evidence: String
    var id: String { name }
}

struct PricingQuote: Codable, Hashable, Sendable {
    let regionId: String
    let regionName: String
    let persona: PricingPersonaKey
    let basePremium: Double
    let suggestedPremium: Double
    let riskMultiplier: Double
    let band: PricingBand
    let drivers: [PricingDriver]
    let confidence: Double
    let methodology: String
    let alpha: Double
    let beta: Double
    let riskFactor: Double
    let tierLoading: Double
    let caveats: [String]
}
