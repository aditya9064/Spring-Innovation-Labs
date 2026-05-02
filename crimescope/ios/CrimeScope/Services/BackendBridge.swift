import Foundation
import CoreLocation

// MARK: - Raw backend DTOs
// These mirror the FastAPI backend's JSON shape exactly.
// Translation to the app's richer iOS contracts happens in `BackendBridge`.

struct BackendScoresResponse: Decodable {
    let tracts: [BackendScore]
}

struct BackendScore: Decodable {
    let tract_geoid: String?
    let NAMELSAD: String?
    let risk_score: Double?
    let baseline_predicted: Double?
    let violent_score: Double?
    let property_score: Double?
    let risk_tier: String?
    let model_vs_baseline: Double?
    let trend_direction: String?
    let scored_at: String?
    let total_pop_acs: Double?
    let median_hh_income_acs: Double?
    let poverty_rate_acs: Double?
    let predicted_next_30d: Double?
    let incident_count: Double?
}

struct BackendDriver: Decodable {
    let name: String
    let direction: String
    let impact: String
    let evidence: String
}

struct BackendTrustPassport: Decodable {
    let confidence: String
    let completeness: String
    let freshness: String
    let sourceAgreement: String
    let underreportingRisk: String
    let action: String
}

struct BackendLiveDisagreement: Decodable {
    let status: String
    let summary: String
    let delta: Int
}

struct BackendWhatChanged: Decodable {
    let summary: String
    let topChanges: [String]
}

struct BackendScoreBreakdown: Decodable {
    let overall: Int
    let violent: Int
    let property: Int
}

struct BackendRiskPackage: Decodable {
    let regionId: String
    let regionType: String?
    let regionName: String
    let city: String?
    let timeHorizonDays: Int?
    let riskLevel: String
    let baselineScore: Int
    let mlScore: Int
    let scores: BackendScoreBreakdown
    let drivers: [BackendDriver]
    let trustPassport: BackendTrustPassport
    let liveDisagreement: BackendLiveDisagreement
    let whatChanged: BackendWhatChanged
    let updatedAt: Date
}

// MARK: - GeoJSON

struct BackendGeoCollection: Decodable {
    let type: String
    let features: [BackendGeoFeature]
}

struct BackendGeoFeature: Decodable {
    let type: String
    let properties: BackendGeoProperties
    let geometry: BackendGeometry
}

struct BackendGeoProperties: Decodable {
    let tract_geoid: String?
    let name: String?
    let risk_score: Double?
    let risk_tier: String?
    let predicted_next_30d: Double?
    let violent_score: Double?
    let property_score: Double?
    let incident_count: Double?
}

/// Handles both Polygon and MultiPolygon geometries.
/// Output is a flat list of rings (outer ring of each polygon).
struct BackendGeometry: Decodable {
    let type: String
    let outerRings: [[[Double]]]

    enum CodingKeys: String, CodingKey { case type, coordinates }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        type = try c.decode(String.self, forKey: .type)
        switch type {
        case "Polygon":
            // coordinates: [[[Double]]] = [ring][point][lon,lat]
            let rings = try c.decode([[[Double]]].self, forKey: .coordinates)
            outerRings = rings.isEmpty ? [] : [rings[0]]
        case "MultiPolygon":
            // coordinates: [[[[Double]]]] = [polygon][ring][point][lon,lat]
            let polys = try c.decode([[[[Double]]]].self, forKey: .coordinates)
            outerRings = polys.compactMap { $0.first }
        default:
            outerRings = []
        }
    }
}

// MARK: - Compare

struct BackendCompareResponse: Decodable {
    let left: BackendCompareSnapshot
    let right: BackendCompareSnapshot
    let summary: String
}

struct BackendCompareSnapshot: Decodable {
    let regionId: String
    let regionName: String
    let city: String?
    let geographyType: String?
    let score: Int
    let baselineScore: Int
    let mlScore: Int
    let confidence: Double
    let completeness: Double
    let freshnessHours: Int
    let trustStatus: String
    let underreportingRisk: String
    let topDrivers: [BackendCompareDriver]
    let recommendation: BackendCompareRecommendation
    let liveDisagreement: BackendLiveDisagreement
}

struct BackendCompareDriver: Decodable {
    let name: String
    let direction: String
    let impact: Double
    let summary: String
}

struct BackendCompareRecommendation: Decodable {
    let persona: String
    let label: String
    let nextStep: String
    let caveat: String
    let reviewRequired: Bool
}

// MARK: - Live (sample data on backend)

struct BackendLiveEvent: Decodable {
    let id: String
    let title: String
    let status: String
    let confidence: String
    let sourceType: String
    let occurredAt: Date
    let resolvedRegionId: String
    let lat: Double
    let lng: Double
    let summary: String
}

// MARK: - Mapping helpers

enum BackendMap {
    static func tier(_ raw: String?) -> RiskTier {
        switch raw?.lowercased() ?? "" {
        case "critical": return .critical
        case "high": return .high
        case "elevated": return .elevated
        case "moderate": return .moderate
        case "low": return .low
        default: return .moderate
        }
    }

    /// String impact (high/medium/low) → 0..1
    static func impactValue(_ raw: String) -> Double {
        switch raw.lowercased() {
        case "high": return 0.85
        case "medium", "moderate": return 0.55
        case "low": return 0.25
        default: return 0.4
        }
    }

    static func direction(_ raw: String) -> Driver.Direction {
        switch raw.lowercased() {
        case "up": return .up
        case "down": return .down
        default: return .neutral
        }
    }

    /// Trust strings → 0..1 quality value (higher = better)
    static func trustValue(_ raw: String) -> Double {
        switch raw.lowercased() {
        case "high", "live", "strong": return 0.92
        case "moderate", "recent", "mixed": return 0.7
        case "low", "stale", "weak": return 0.35
        case "unknown": return 0.5
        default: return 0.6
        }
    }

    /// Underreporting risk string → 0..1 (higher = more risk)
    static func risk(_ raw: String) -> Double {
        switch raw.lowercased() {
        case "high": return 0.85
        case "moderate": return 0.5
        case "low": return 0.15
        default: return 0.4
        }
    }

    static func centroid(of ring: [[Double]]) -> Coordinate {
        guard !ring.isEmpty else { return Coordinate(latitude: 0, longitude: 0) }
        var sumLat: Double = 0
        var sumLng: Double = 0
        for p in ring where p.count >= 2 {
            sumLng += p[0]
            sumLat += p[1]
        }
        let n = Double(ring.count)
        return Coordinate(latitude: sumLat / n, longitude: sumLng / n)
    }

    static func parseDate(_ raw: String?) -> Date {
        guard let raw else { return Date() }
        if let d = ISO8601DateFormatter.fractional.date(from: raw) { return d }
        if let d = ISO8601DateFormatter.plain.date(from: raw) { return d }
        for f in DateFormatter.backendCandidates {
            if let d = f.date(from: raw) { return d }
        }
        return Date()
    }

    /// Map a BackendScore + (optional) centroid to TractScore
    static func tractScore(from b: BackendScore, centroid: Coordinate?) -> TractScore? {
        guard let geoid = b.tract_geoid, let score = b.risk_score else { return nil }
        let tier = tier(b.risk_tier)
        let base = b.baseline_predicted ?? score
        let ml = score
        let confidence = max(0.4, 1.0 - min(0.4, abs(b.model_vs_baseline ?? 0)))
        let trend: TrendDirection? = {
            guard let raw = b.trend_direction?.lowercased() else { return nil }
            return TrendDirection(rawValue: raw)
        }()
        return TractScore(
            geoid: geoid,
            name: b.NAMELSAD ?? "Tract \(geoid.suffix(4))",
            tier: tier,
            score: score,
            baselineScore: base,
            mlScore: ml,
            violentScore: b.violent_score ?? score,
            propertyScore: b.property_score ?? score,
            centroid: centroid ?? MockData.centroidNear(geoid: geoid),
            confidence: confidence,
            lastUpdated: parseDate(b.scored_at),
            predictedNext30d: b.predicted_next_30d ?? 0,
            trendDirection: trend
        )
    }

    static func tractPolygon(from f: BackendGeoFeature) -> TractPolygon? {
        guard let geoid = f.properties.tract_geoid,
              let ring = f.geometry.outerRings.first,
              ring.count >= 3 else { return nil }
        let coords = ring.compactMap { p -> Coordinate? in
            guard p.count >= 2 else { return nil }
            return Coordinate(latitude: p[1], longitude: p[0])
        }
        return TractPolygon(
            geoid: geoid,
            coordinates: coords,
            tier: tier(f.properties.risk_tier),
            score: f.properties.risk_score ?? 0
        )
    }

    static func driver(from b: BackendDriver, index: Int) -> Driver {
        Driver(
            id: "drv-\(index)-\(b.name.hashValue)",
            label: b.name,
            direction: direction(b.direction),
            impact: impactValue(b.impact),
            evidence: b.evidence,
            category: "ml"
        )
    }

    static func trustPassport(from b: BackendTrustPassport) -> TrustPassport {
        TrustPassport(
            confidence: trustValue(b.confidence),
            completeness: trustValue(b.completeness),
            freshness: trustValue(b.freshness),
            sourceAgreement: trustValue(b.sourceAgreement),
            underreportingRisk: risk(b.underreportingRisk),
            recommendedAction: b.action.capitalized,
            summary: "Confidence \(b.confidence). Completeness \(b.completeness). Freshness \(b.freshness). Sources \(b.sourceAgreement)."
        )
    }

    static func whatChangedItems(from b: BackendWhatChanged) -> [WhatChangedItem] {
        b.topChanges.enumerated().map { idx, raw in
            // Backend strings tend to be like "Foo (high impact) increases the risk score. Current value: 32.0..."
            let parts = raw.components(separatedBy: ".")
            let label = parts.first?.trimmingCharacters(in: .whitespacesAndNewlines) ?? raw
            let detail = parts.dropFirst().joined(separator: ".").trimmingCharacters(in: .whitespacesAndNewlines)
            let delta: Double = raw.lowercased().contains("decrease") ? -1 : raw.lowercased().contains("increase") ? 1 : 0
            return WhatChangedItem(
                id: "chg-\(idx)",
                label: label.isEmpty ? "Update \(idx + 1)" : label,
                delta: delta,
                detail: detail.isEmpty ? raw : detail
            )
        }
    }

    static func personaDecisions(from pkg: BackendRiskPackage, persona: Persona) -> [PersonaDecision] {
        let trust = trustPassport(from: pkg.trustPassport)
        let actionLower = pkg.trustPassport.action.lowercased()
        let recommendation = personaRecommendation(persona: persona, action: actionLower, riskLevel: pkg.riskLevel)
        let nextSteps = personaNextSteps(persona: persona, action: actionLower)
        let caveats: [String] = {
            var out: [String] = []
            if pkg.trustPassport.confidence.lowercased() == "low" {
                out.append("Confidence is low — verify with on-the-ground sources before acting.")
            }
            if pkg.trustPassport.underreportingRisk.lowercased() == "high" {
                out.append("Underreporting risk is high — true incidence may exceed observed values.")
            }
            if pkg.liveDisagreement.status == "divergent" {
                out.append("ML and baseline disagree — score-of-record is the verified baseline.")
            }
            return out
        }()
        return [PersonaDecision(
            persona: persona,
            recommendation: recommendation,
            confidence: trust.confidence,
            nextSteps: nextSteps,
            caveats: caveats
        )]
    }

    private static func personaRecommendation(persona: Persona, action: String, riskLevel: String) -> String {
        switch persona {
        case .insurance:
            if action.contains("manual") { return "Send to manual underwriting" }
            if action.contains("conditional") { return "Conditional accept with surcharge" }
            return "Standard underwriting"
        case .publicSafety:
            switch riskLevel.lowercased() {
            case "critical", "high": return "Increase patrol frequency"
            case "elevated": return "Targeted deployment during peak windows"
            default: return "Maintain baseline patrols"
            }
        case .logistics:
            switch riskLevel.lowercased() {
            case "critical", "high": return "Avoid late-night windows; daylight only"
            case "elevated": return "Restrict to daylight + duo crews"
            default: return "Route normally"
            }
        case .real_estate:
            switch riskLevel.lowercased() {
            case "critical": return "High-risk disclosure required"
            case "high", "elevated": return "Disclose risk in listing materials"
            default: return "Standard disclosure"
            }
        case .civic:
            return "Cross-reference with equity dashboard before action"
        case .journalist:
            return "Verify with at least two independent sources"
        }
    }

    private static func personaNextSteps(persona: Persona, action: String) -> [String] {
        switch persona {
        case .insurance:
            return ["Pull last 24 mo of claims", "Compare to peer tracts in same tier", "Document override rationale if departing from action: \(action)"]
        case .publicSafety:
            return ["Review CAD logs for last 7 days", "Coordinate with adjacent districts", "Schedule community follow-up"]
        case .logistics:
            return ["Validate driver schedules against the recommendation", "Update routing software", "Notify affected accounts"]
        case .real_estate:
            return ["Prepare disclosure addendum", "Compare to comp set", "Note in MLS"]
        case .civic:
            return ["Pull census ACS demographics", "Cross-check 311 service requests", "Include in monthly equity report"]
        case .journalist:
            return ["Confirm with second source", "Pull FOIA records for the tract", "Cite scoring methodology"]
        }
    }

    static func riskPackage(from pkg: BackendRiskPackage, persona: Persona) -> TractRiskPackage {
        TractRiskPackage(
            geoid: pkg.regionId,
            name: pkg.regionName,
            riskLevel: pkg.riskLevel.capitalized,
            scores: TractRiskPackage.Scores(
                overall: Double(pkg.scores.overall),
                violent: Double(pkg.scores.violent),
                property: Double(pkg.scores.property)
            ),
            baselineScore: Double(pkg.baselineScore),
            mlScore: Double(pkg.mlScore),
            trustPassport: trustPassport(from: pkg.trustPassport),
            drivers: pkg.drivers.enumerated().map { driver(from: $1, index: $0) },
            whatChanged: whatChangedItems(from: pkg.whatChanged),
            personaDecisions: personaDecisions(from: pkg, persona: persona),
            liveDisagreement: liveDisagreement(from: pkg.liveDisagreement),
            lastUpdated: pkg.updatedAt
        )
    }

    static func liveDisagreement(from b: BackendLiveDisagreement) -> LiveDisagreement {
        let status: LiveDisagreement.Status = {
            switch b.status.lowercased() {
            case "aligned": return .aligned
            case "divergent": return .divergent
            default: return .watch
            }
        }()
        return LiveDisagreement(status: status, summary: b.summary, delta: b.delta)
    }

    static func compareSnapshot(from b: BackendCompareSnapshot) -> CompareSnapshot {
        let trust = TrustPassport(
            confidence: b.confidence,
            completeness: b.completeness,
            freshness: max(0, 1 - Double(b.freshnessHours) / 168.0),
            sourceAgreement: b.trustStatus.lowercased() == "verified" ? 0.92 : 0.6,
            underreportingRisk: risk(b.underreportingRisk),
            recommendedAction: b.recommendation.label.capitalized,
            summary: b.recommendation.caveat
        )
        let drivers: [Driver] = b.topDrivers.enumerated().map { idx, d in
            Driver(
                id: "cmp-drv-\(idx)",
                label: d.name,
                direction: direction(d.direction),
                impact: max(0.1, min(1.0, d.impact)),
                evidence: d.summary,
                category: "ml"
            )
        }
        return CompareSnapshot(
            geoid: b.regionId,
            name: b.regionName,
            tier: scoreTier(b.score),
            score: Double(b.score),
            baselineScore: Double(b.baselineScore),
            mlScore: Double(b.mlScore),
            trust: trust,
            topDrivers: drivers,
            liveDelta: Double(b.liveDisagreement.delta),
            recommendation: b.recommendation.label.capitalized + " · " + b.recommendation.nextStep
        )
    }

    static func liveEvent(from b: BackendLiveEvent) -> LiveEvent {
        LiveEvent(
            id: b.id,
            geoid: b.resolvedRegionId,
            regionName: "Region \(b.resolvedRegionId.suffix(4))",
            category: b.title,
            source: liveSource(b.sourceType),
            status: liveStatus(b.status),
            confidence: trustValue(b.confidence),
            summary: b.summary,
            occurredAt: b.occurredAt
        )
    }

    private static func liveSource(_ raw: String) -> LiveEvent.Source {
        switch raw.lowercased() {
        case "911", "dispatch", "dispatch_911": return .dispatch_911
        case "fire": return .fire
        case "sensor": return .sensor
        case "social": return .social
        case "news": return .news
        default: return .crowdsource
        }
    }

    private static func liveStatus(_ raw: String) -> LiveEvent.Status {
        switch raw.lowercased() {
        case "verified": return .verified
        case "pending": return .pending
        default: return .unverified
        }
    }

    private static func scoreTier(_ s: Int) -> RiskTier {
        Format.tierFromScore(Double(s))
    }
}

// MARK: - Date helpers

extension ISO8601DateFormatter {
    static let fractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    static let plain: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()
}

extension DateFormatter {
    static let backendCandidates: [DateFormatter] = {
        let formats = [
            "yyyy-MM-dd'T'HH:mm:ss.SSS",
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd HH:mm:ss"
        ]
        return formats.map { fmt in
            let f = DateFormatter()
            f.locale = Locale(identifier: "en_US_POSIX")
            f.timeZone = TimeZone(secondsFromGMT: 0)
            f.calendar = Calendar(identifier: .iso8601)
            f.dateFormat = fmt
            return f
        }
    }()
}

// MARK: - MockData fallback helpers

extension MockData {
    /// Stable fallback centroid for tracts when polygon hasn't loaded yet.
    static func centroidNear(geoid: String) -> Coordinate {
        var hash: UInt64 = 5381
        for ch in geoid.utf8 { hash = ((hash << 5) &+ hash) &+ UInt64(ch) }
        var rng = SeededRandom(seed: hash)
        return Coordinate(
            latitude: chicagoCenter.latitude + rng.uniform(-0.18, 0.18),
            longitude: chicagoCenter.longitude + rng.uniform(-0.22, 0.22)
        )
    }
}
