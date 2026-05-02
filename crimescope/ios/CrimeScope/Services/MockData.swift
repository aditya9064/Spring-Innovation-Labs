import Foundation
import CoreLocation

enum MockData {
    static let chicagoCenter = CLLocationCoordinate2D(latitude: 41.8781, longitude: -87.6298)
    /// Geographical centre of England & Wales — sits over the Welsh Marches
    /// (Shropshire / Powys border) so the default view shows both nations.
    static let ukCenter = CLLocationCoordinate2D(latitude: 52.6, longitude: -2.0)
    static let walesCenter = CLLocationCoordinate2D(latitude: 52.13, longitude: -3.78)

    static func defaultCenter(forCity city: String) -> CLLocationCoordinate2D {
        switch city {
        case "chicago": return chicagoCenter
        case "uk", "uk_lsoa": return ukCenter
        default: return ukCenter
        }
    }

    static func defaultAltitude(forCity city: String) -> Double {
        switch city {
        case "chicago": return 28000
        case "uk", "uk_lsoa": return 1_400_000  // wide enough to frame all of E&W
        default: return 1_400_000
        }
    }

    private static let neighborhoods: [String] = [
        "West Loop", "Loop", "River North", "Streeterville", "Gold Coast",
        "Lincoln Park", "Lakeview", "Wicker Park", "Logan Square", "Bucktown",
        "Pilsen", "Bridgeport", "Chinatown", "Hyde Park", "Kenwood",
        "Englewood", "Garfield Park", "Austin", "Humboldt Park", "Albany Park",
        "Uptown", "Edgewater", "Rogers Park", "North Center", "Roscoe Village",
        "Avondale", "Belmont Cragin", "Hermosa", "Portage Park", "Irving Park",
        "Old Town", "Near North", "South Loop", "Printers Row", "Greektown",
        "Little Italy", "Tri-Taylor", "East Garfield", "Lawndale", "Douglas",
        "Bronzeville", "Washington Park", "Woodlawn", "South Shore", "Avalon Park",
        "Chatham", "Roseland", "Pullman", "Hegewisch", "Mount Greenwood"
    ]

    static let tracts: [TractScore] = generateTracts()

    private static func generateTracts() -> [TractScore] {
        var seedRng = SeededRandom(seed: 42)
        return (0..<50).map { i in
            let lat = chicagoCenter.latitude + seedRng.uniform(-0.12, 0.12)
            let lng = chicagoCenter.longitude + seedRng.uniform(-0.16, 0.16)
            let baseScore = seedRng.uniform(20, 92)
            let mlAdjustment = seedRng.uniform(-6, 6)
            let mlScore = max(0, min(100, baseScore + mlAdjustment))
            let overall = (baseScore + mlScore) / 2
            let trendPick = seedRng.uniform(0, 1)
            let trend: TrendDirection = trendPick < 0.33 ? .rising : trendPick < 0.66 ? .stable : .falling
            return TractScore(
                geoid: String(format: "17031%06d", 100100 + i * 113),
                name: neighborhoods[i],
                tier: Format.tierFromScore(overall),
                score: overall,
                baselineScore: baseScore,
                mlScore: mlScore,
                violentScore: max(0, min(100, overall + seedRng.uniform(-12, 6))),
                propertyScore: max(0, min(100, overall + seedRng.uniform(-8, 12))),
                centroid: Coordinate(latitude: lat, longitude: lng),
                confidence: seedRng.uniform(0.55, 0.96),
                lastUpdated: Date().addingTimeInterval(-seedRng.uniform(60, 86400 * 4)),
                predictedNext30d: max(0, overall * seedRng.uniform(0.08, 0.18)),
                trendDirection: trend
            )
        }
    }

    static func polygonsForTracts(_ tracts: [TractScore]) -> [TractPolygon] {
        tracts.map { tract in
            TractPolygon(
                geoid: tract.geoid,
                coordinates: hexagon(around: tract.centroid, radiusKm: 0.9),
                tier: tract.tier,
                score: tract.score
            )
        }
    }

    private static func hexagon(around center: Coordinate, radiusKm: Double) -> [Coordinate] {
        let radiusDeg = radiusKm / 111.0
        return (0..<6).map { i in
            let angle = Double(i) * .pi / 3.0
            let lat = center.latitude + radiusDeg * sin(angle)
            let lng = center.longitude + radiusDeg * cos(angle) /
                cos(center.latitude * .pi / 180.0)
            return Coordinate(latitude: lat, longitude: lng)
        }
    }

    static func riskPackage(for tract: TractScore) -> TractRiskPackage {
        var rng = SeededRandom(seed: UInt64(abs(tract.geoid.hashValue)))
        let drivers: [Driver] = [
            Driver(
                id: "d1",
                label: "911 dispatch volume +18% vs 90d avg",
                direction: .up,
                impact: rng.uniform(0.55, 0.85),
                evidence: "CPD dispatch logs · last 14 days",
                category: "live"
            ),
            Driver(
                id: "d2",
                label: "Verified violent UCR baseline",
                direction: .up,
                impact: rng.uniform(0.40, 0.70),
                evidence: "FBI UCR · 5-year rolling",
                category: "baseline"
            ),
            Driver(
                id: "d3",
                label: "Income / unemployment context",
                direction: .neutral,
                impact: rng.uniform(0.20, 0.45),
                evidence: "ACS 5-year · 2023",
                category: "context"
            ),
            Driver(
                id: "d4",
                label: "Streetlight uptime improved",
                direction: .down,
                impact: rng.uniform(0.15, 0.35),
                evidence: "311 service requests",
                category: "intervention"
            ),
            Driver(
                id: "d5",
                label: "Reporting consistency moderate",
                direction: .neutral,
                impact: rng.uniform(0.10, 0.30),
                evidence: "Coverage audit · 2025-Q4",
                category: "trust"
            )
        ]

        let whatChanged: [WhatChangedItem] = [
            WhatChangedItem(id: "w1", label: "Live 911 spike", delta: rng.uniform(2.5, 5.5), detail: "Dispatch density up vs prior week"),
            WhatChangedItem(id: "w2", label: "Sensor agreement", delta: rng.uniform(-2.0, -0.5), detail: "ShotSpotter & 911 reconciled"),
            WhatChangedItem(id: "w3", label: "Baseline drift", delta: rng.uniform(-0.5, 1.5), detail: "Quarterly UCR refresh"),
            WhatChangedItem(id: "w4", label: "Civic context", delta: rng.uniform(-1.0, 0.5), detail: "Permit & investment activity")
        ]

        let trust = TrustPassport(
            confidence: rng.uniform(0.55, 0.95),
            completeness: rng.uniform(0.6, 0.98),
            freshness: rng.uniform(0.4, 0.95),
            sourceAgreement: rng.uniform(0.55, 0.92),
            underreportingRisk: rng.uniform(0.05, 0.45),
            recommendedAction: tract.score > 70
                ? "Use baseline. Treat live spike as supporting evidence, not score-of-record."
                : "Score-of-record. Live signals broadly agree with verified history.",
            summary: tract.score > 70
                ? "Verified history shows elevated risk; live signals concur with moderate noise."
                : "Verified history is stable; recent signals add minor color but don't move the score."
        )

        let recommendation: String
        switch Format.tierFromScore(tract.score) {
        case .critical:
            recommendation = "Refer to manual underwriting · senior analyst review"
        case .high:
            recommendation = "Manual review · request additional context"
        case .elevated:
            recommendation = "Auto-approve with elevated premium · re-check in 30d"
        case .moderate, .low:
            recommendation = "Auto-approve at standard tier"
        }

        let personas: [PersonaDecision] = Persona.allCases.map { persona in
            PersonaDecision(
                persona: persona,
                recommendation: recommendation,
                confidence: rng.uniform(0.55, 0.92),
                nextSteps: [
                    "Pull last 90 days of dispatch by hour",
                    "Compare against peer tracts in tier",
                    "Note live disagreement in the file"
                ],
                caveats: [
                    "Underreporting risk is non-zero — score may be conservative.",
                    "Live signals are advisory; do not override the baseline silently."
                ]
            )
        }

        let mlMinusBase = Int(tract.mlScore - tract.baselineScore)
        let absDelta = abs(mlMinusBase)
        let status: LiveDisagreement.Status
        let summary: String
        if absDelta < 3 {
            status = .aligned
            summary = "ML and baseline agree closely for this region."
        } else if absDelta < 9 {
            status = .watch
            summary = "Moderate divergence between ML and baseline; monitor live signals."
        } else {
            status = .divergent
            summary = "Significant divergence — verified baseline is the score-of-record."
        }
        let disagreement = LiveDisagreement(status: status, summary: summary, delta: mlMinusBase)
        return TractRiskPackage(
            geoid: tract.geoid,
            name: tract.name,
            riskLevel: tract.tier.rawValue,
            scores: .init(overall: tract.score, violent: tract.violentScore, property: tract.propertyScore),
            baselineScore: tract.baselineScore,
            mlScore: tract.mlScore,
            trustPassport: trust,
            drivers: drivers,
            whatChanged: whatChanged,
            personaDecisions: personas,
            liveDisagreement: disagreement,
            lastUpdated: tract.lastUpdated
        )
    }

    static func liveEvents(for geoid: String? = nil, limit: Int = 30) -> [LiveEvent] {
        var rng = SeededRandom(seed: UInt64(abs((geoid ?? "city").hashValue)))
        let sources: [LiveEvent.Source] = [.dispatch_911, .fire, .sensor, .social, .news, .crowdsource]
        let statuses: [LiveEvent.Status] = [.verified, .pending, .unverified]
        let categories = ["assault", "burglary", "vehicle theft", "vandalism", "noise", "fire", "medical"]
        let summaries = [
            "911 dispatch reported aggravated assault near transit",
            "ShotSpotter detected discharge cluster",
            "Crowdsource report: vehicle break-in on residential block",
            "Fire response cleared at commercial structure",
            "Twitter trend: protest activity reported peaceful",
            "News alert: DoJ press conference referencing district",
            "Sensor anomaly resolved without dispatch"
        ]
        let pool = MockData.tracts
        return (0..<limit).map { i in
            let tract: TractScore
            if let geoid, let match = pool.first(where: { $0.geoid == geoid }) {
                tract = match
            } else {
                tract = pool[Int(rng.uniform(0, Double(pool.count - 1)))]
            }
            return LiveEvent(
                id: UUID().uuidString,
                geoid: tract.geoid,
                regionName: tract.name,
                category: categories[Int(rng.uniform(0, Double(categories.count - 1)))],
                source: sources[Int(rng.uniform(0, Double(sources.count - 1)))],
                status: statuses[Int(rng.uniform(0, Double(statuses.count - 1)))],
                confidence: rng.uniform(0.4, 0.95),
                summary: summaries[Int(rng.uniform(0, Double(summaries.count - 1)))],
                occurredAt: Date().addingTimeInterval(-rng.uniform(30, 60 * 60 * 12))
            )
        }
    }

    static func interventions() -> [Intervention] {
        [
            Intervention(id: "patrol", label: "Patrol density", description: "Officer-hours per shift in tract", unit: "hrs", minValue: 0, maxValue: 40, defaultValue: 12, estimatedImpact: -0.18),
            Intervention(id: "lighting", label: "Streetlight uptime", description: "Restored & monitored fixtures", unit: "%", minValue: 50, maxValue: 100, defaultValue: 82, estimatedImpact: -0.07),
            Intervention(id: "youth", label: "Youth programs", description: "Active program slots", unit: "slots", minValue: 0, maxValue: 600, defaultValue: 120, estimatedImpact: -0.05),
            Intervention(id: "cameras", label: "Public cameras", description: "Network-monitored cameras", unit: "units", minValue: 0, maxValue: 60, defaultValue: 14, estimatedImpact: -0.06),
            Intervention(id: "outreach", label: "Violence interruption", description: "Active interrupters", unit: "FTE", minValue: 0, maxValue: 12, defaultValue: 3, estimatedImpact: -0.09)
        ]
    }

    static func simulate(pkg: TractRiskPackage, values: [String: Double]) -> SimulationResult {
        let baseline = pkg.scores.overall
        let interventions = self.interventions()
        var deltas: [SimulationResult.Breakdown] = []
        var totalDelta: Double = 0
        for intervention in interventions {
            let value = values[intervention.id] ?? intervention.defaultValue
            let normalized = (value - intervention.minValue) / max(0.0001, intervention.maxValue - intervention.minValue)
            let delta = intervention.estimatedImpact * normalized * 100
            deltas.append(.init(id: intervention.id, label: intervention.label, delta: delta))
            totalDelta += delta
        }
        let projected = max(0, min(100, baseline + totalDelta))
        let projectedTier = Format.tierFromScore(projected)
        let narrative: String
        if abs(totalDelta) < 1 {
            narrative = "Modeled interventions are roughly neutral; verify with peer tracts before committing."
        } else if totalDelta < 0 {
            narrative = "Combined interventions project a \(Format.score(abs(totalDelta)))-point reduction; biggest lever is the dominant negative driver below."
        } else {
            narrative = "Modeled values increase projected risk by \(Format.score(totalDelta)) — re-check direction signs."
        }
        return SimulationResult(
            baselineScore: baseline,
            simulatedScore: projected,
            projectedTier: projectedTier,
            narrative: narrative,
            breakdown: deltas
        )
    }

    static func compareSnapshot(for tract: TractScore) -> CompareSnapshot {
        let pkg = riskPackage(for: tract)
        return CompareSnapshot(
            geoid: tract.geoid,
            name: tract.name,
            tier: tract.tier,
            score: tract.score,
            baselineScore: tract.baselineScore,
            mlScore: tract.mlScore,
            trust: pkg.trustPassport,
            topDrivers: Array(pkg.drivers.prefix(3)),
            liveDelta: tract.mlScore - tract.baselineScore,
            recommendation: pkg.personaDecisions.first?.recommendation ?? "Manual review"
        )
    }

    static func report(for tract: TractScore) -> ReportSummary {
        let pkg = riskPackage(for: tract)
        let peers = tracts
            .filter { $0.tier == tract.tier && $0.geoid != tract.geoid }
            .prefix(3)
            .map { ReportSummary.PeerEntry(geoid: $0.geoid, name: $0.name, score: $0.score, tier: $0.tier) }

        return ReportSummary(
            geoid: tract.geoid,
            name: tract.name,
            tier: tract.tier,
            executiveSummary: """
            \(tract.name) is currently scored at \(Format.score(tract.score)) (\(tract.tier.rawValue)). \
            The verified historical baseline is \(Format.score(tract.baselineScore)); the ML-adjusted score is \(Format.score(tract.mlScore)). \
            Trust posture: \(pkg.trustPassport.summary)
            """,
            riskNarrative: """
            Top contributors to the current score include \(pkg.drivers.prefix(3).map(\.label).joined(separator: "; ")). \
            Live signals \(tract.mlScore > tract.baselineScore + 3 ? "diverge upward from" : "broadly agree with") the verified baseline.
            """,
            trustNotes: pkg.trustPassport.recommendedAction,
            drivers: pkg.drivers,
            peerCompare: Array(peers),
            challenges: [
                "No challenges currently registered against this tract.",
                "Last data refresh: \(Format.dateTime(tract.lastUpdated))."
            ],
            generatedAt: Date()
        )
    }
}

struct SeededRandom {
    private var state: UInt64

    init(seed: UInt64) {
        self.state = seed == 0 ? 1 : seed
    }

    mutating func nextDouble() -> Double {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        let value = (state >> 11) & 0x1FFFFFFFFFFFFF
        return Double(value) / Double(1 << 53)
    }

    mutating func uniform(_ minVal: Double, _ maxVal: Double) -> Double {
        minVal + nextDouble() * (maxVal - minVal)
    }
}
