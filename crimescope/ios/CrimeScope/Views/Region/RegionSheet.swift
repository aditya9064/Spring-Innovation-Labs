import SwiftUI

struct RegionSheet: View {
    let tract: TractScore
    @Environment(APIClient.self) private var api
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var pkg: TractRiskPackage?
    @State private var loading = true
    @State private var simulatorPresented = false
    @State private var comparePresented = false
    @State private var lookAroundPresented = false
    @State private var detailsExpanded: Bool = false
    @State private var nearbyPolygons: [TractPolygon] = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                    if loading {
                        LoadingView(label: "Loading risk package…")
                            .frame(height: 240)
                    } else if let pkg {
                        // The 5 verbs from the problem statement, in order:
                        // SCORE → EXPLAIN → PROJECT → ANALYSE patterns → PRICE.
                        RegionScoreHeader(tract: tract, pkg: pkg)
                        RegionSummaryLine(tract: tract, pkg: pkg, persona: store.persona)
                        RegionTrendCard(geoid: pkg.geoid, regionName: pkg.name)
                        RegionBreakdownCard(geoid: pkg.geoid)
                        RegionPricingCard(geoid: pkg.geoid)

                        RegionActionsBar(
                            streetView: { lookAroundPresented = true },
                            simulator: { simulatorPresented = true },
                            compare: { comparePresented = true }
                        )

                        // Everything below is supporting evidence — collapsed
                        // by default to keep the headline answer prominent.
                        DisclosureGroup(isExpanded: $detailsExpanded) {
                            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                                RegionDisagreementBanner(pkg: pkg)
                                RegionTrustPassportCard(passport: pkg.trustPassport)
                                RegionDriversCard(drivers: pkg.drivers)
                                RegionWhatChangedCard(items: pkg.whatChanged)
                                RegionPersonaDecisionCard(pkg: pkg, persona: store.persona)
                            }
                            .padding(.top, Theme.Spacing.md)
                        } label: {
                            HStack {
                                Text(detailsExpanded ? "Hide trust + evidence" : "Show trust + evidence")
                                    .font(Theme.Font.label)
                                    .foregroundStyle(Theme.Color.accent)
                                Spacer()
                            }
                        }
                        .tint(Theme.Color.accent)
                        .padding(.horizontal, 4)
                    }
                }
                .padding(Theme.Spacing.lg)
            }
            .background(Theme.Color.bg)
            .navigationTitle(tract.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        store.toggleWatchlist(tract.geoid)
                    } label: {
                        Image(systemName: store.watchlist.contains(tract.geoid) ? "star.fill" : "star")
                            .foregroundStyle(store.watchlist.contains(tract.geoid) ? Theme.Color.elevated : Theme.Color.textSecondary)
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                        .foregroundStyle(Theme.Color.accent)
                }
            }
        }
        .task { await load() }
        .sheet(isPresented: $simulatorPresented) {
            if let pkg { SimulatorView(pkg: pkg) }
        }
        .sheet(isPresented: $comparePresented) {
            ComparePickerView(left: tract)
        }
        .fullScreenCover(isPresented: $lookAroundPresented) {
            LookAroundView(
                coordinate: tract.centroid.clLocation,
                regionName: tract.name,
                tier: tract.tier,
                score: tract.score,
                polygons: nearbyPolygons,
                selectedGeoid: tract.geoid
            )
        }
    }

    private func load() async {
        loading = true
        async let pkgTask = api.fetchRiskPackage(geoid: tract.geoid)
        async let polysTask = api.fetchPolygons(city: store.city)
        let (result, polys) = await (pkgTask, polysTask)
        await MainActor.run {
            self.pkg = result
            self.nearbyPolygons = polys
            self.loading = false
        }
    }
}

struct RegionScoreHeader: View {
    let tract: TractScore
    let pkg: TractRiskPackage

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(tract.name)
                            .font(Theme.Font.titleLarge)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Text(Format.shortGeoid(tract.geoid))
                            .font(Theme.Font.mono)
                            .foregroundStyle(Theme.Color.textMuted)
                    }
                    Spacer()
                    TierPill(tier: pkg.scores.overall.asTier, size: .lg, withScore: pkg.scores.overall)
                }

                Divider().background(Theme.Color.border)

                HStack(spacing: Theme.Spacing.lg) {
                    ScoreNumber(value: pkg.baselineScore, label: "Baseline", size: .md)
                    ScoreNumber(value: pkg.mlScore, label: "ML-Adjusted", size: .md, tint: Theme.Color.accent)
                    DeltaPill(delta: pkg.mlScore - pkg.baselineScore)
                }

                HStack(spacing: Theme.Spacing.xl) {
                    miniScore(label: "Violent", value: pkg.scores.violent)
                    miniScore(label: "Property", value: pkg.scores.property)
                    if tract.predictedNext30d > 0 {
                        miniScore(label: "Next 30D", value: tract.predictedNext30d, tint: Theme.Color.accent)
                    }
                    Spacer()
                    Text("Updated \(Format.timeAgo(pkg.lastUpdated))")
                        .font(Theme.Font.monoCaption)
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
        }
    }

    private func miniScore(label: String, value: Double, tint: Color? = nil) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(Theme.Font.monoCaption)
                .tracking(0.6)
                .foregroundStyle(Theme.Color.textMuted)
            Text(Format.score(value))
                .font(Theme.Font.mono)
                .foregroundStyle(tint ?? Theme.Color.textSecondary)
                .monospacedDigit()
        }
    }
}

struct RegionDisagreementBanner: View {
    let pkg: TractRiskPackage

    var body: some View {
        // Drives off the backend's authoritative `liveDisagreement` payload —
        // not a re-derived heuristic — so the banner matches what other
        // surfaces (compare, audit) display for the same region.
        let dis = pkg.liveDisagreement
        let isDiverging = dis.status != .aligned
        let tone: Color = dis.delta > 0 ? Theme.Color.high : dis.delta < 0 ? Theme.Color.low : Theme.Color.textSecondary
        let statusLabel: String = {
            switch dis.status {
            case .aligned: return "Verified vs Live: aligned"
            case .watch: return "Verified vs Live: watch"
            case .divergent: return "Verified vs Live: divergent"
            }
        }()

        return Card(background: isDiverging ? tone.opacity(0.12) : Theme.Color.bgPanel) {
            HStack(alignment: .top, spacing: Theme.Spacing.md) {
                Image(systemName: isDiverging ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                    .foregroundStyle(isDiverging ? tone : Theme.Color.low)
                    .font(.system(size: 18))

                VStack(alignment: .leading, spacing: 4) {
                    Text(statusLabel)
                        .font(Theme.Font.title)
                        .foregroundStyle(Theme.Color.textPrimary)
                    Text(dis.summary)
                        .font(Theme.Font.body)
                        .foregroundStyle(Theme.Color.textSecondary)
                    if dis.delta != 0 {
                        Text("Δ \(dis.delta > 0 ? "+" : "")\(dis.delta) pts vs baseline")
                            .font(Theme.Font.monoCaption)
                            .tracking(0.6)
                            .foregroundStyle(Theme.Color.textMuted)
                    }
                }
            }
        }
    }
}

struct RegionTrustPassportCard: View {
    let passport: TrustPassport

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Trust Passport", caption: passport.summary)

                metricGrid

                Divider().background(Theme.Color.border)

                VStack(alignment: .leading, spacing: 4) {
                    Text("RECOMMENDED ACTION")
                        .font(Theme.Font.monoCaption)
                        .foregroundStyle(Theme.Color.textMuted)
                        .tracking(0.6)
                    Text(passport.recommendedAction)
                        .font(Theme.Font.body)
                        .foregroundStyle(Theme.Color.textPrimary)
                }
            }
        }
    }

    private var metricGrid: some View {
        let metrics: [(String, Double, Bool)] = [
            ("Confidence", passport.confidence, false),
            ("Completeness", passport.completeness, false),
            ("Freshness", passport.freshness, false),
            ("Source agreement", passport.sourceAgreement, false),
            ("Underreporting risk", passport.underreportingRisk, true)
        ]

        return VStack(spacing: 8) {
            ForEach(metrics, id: \.0) { name, value, inverted in
                metricRow(name: name, value: value, inverted: inverted)
            }
        }
    }

    private func metricRow(name: String, value: Double, inverted: Bool) -> some View {
        let displayValue = inverted ? value : value
        let goodness = inverted ? 1 - value : value
        let color: Color = goodness > 0.75 ? Theme.Color.low : goodness > 0.5 ? Theme.Color.elevated : Theme.Color.high

        return HStack(spacing: Theme.Spacing.md) {
            Text(name)
                .font(Theme.Font.label)
                .foregroundStyle(Theme.Color.textSecondary)
                .frame(width: 150, alignment: .leading)

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Theme.Color.border)
                        .frame(height: 4)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(color)
                        .frame(width: geo.size.width * displayValue, height: 4)
                }
            }
            .frame(height: 4)

            Text(Format.percent(displayValue))
                .font(Theme.Font.mono)
                .foregroundStyle(color)
                .frame(width: 44, alignment: .trailing)
                .monospacedDigit()
        }
    }
}

struct RegionPersonaDecisionCard: View {
    let pkg: TractRiskPackage
    let persona: Persona

    private var decision: PersonaDecision? {
        pkg.personaDecisions.first { $0.persona == persona }
            ?? pkg.personaDecisions.first
    }

    var body: some View {
        Card(background: Theme.Color.accent.opacity(0.08)) {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                HStack {
                    SectionHeader(title: "\(persona.displayName) recommendation")
                    Spacer()
                    if let confidence = decision?.confidence {
                        Text(Format.percent(confidence) + " conf.")
                            .font(Theme.Font.mono)
                            .foregroundStyle(Theme.Color.accent)
                    }
                }

                Text(decision?.recommendation ?? "Manual review recommended.")
                    .font(Theme.Font.titleLarge)
                    .foregroundStyle(Theme.Color.textPrimary)

                if let next = decision?.nextSteps, !next.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("NEXT STEPS")
                            .font(Theme.Font.monoCaption)
                            .foregroundStyle(Theme.Color.textMuted)
                            .tracking(0.6)
                        ForEach(next, id: \.self) { step in
                            HStack(alignment: .top, spacing: 6) {
                                Text("›")
                                    .foregroundStyle(Theme.Color.accent)
                                Text(step)
                                    .font(Theme.Font.body)
                                    .foregroundStyle(Theme.Color.textPrimary)
                            }
                        }
                    }
                }

                if let caveats = decision?.caveats, !caveats.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("CAVEATS")
                            .font(Theme.Font.monoCaption)
                            .foregroundStyle(Theme.Color.textMuted)
                            .tracking(0.6)
                        ForEach(caveats, id: \.self) { c in
                            Text("· \(c)")
                                .font(Theme.Font.body)
                                .foregroundStyle(Theme.Color.textSecondary)
                        }
                    }
                }
            }
        }
    }
}

struct RegionWhatChangedCard: View {
    let items: [WhatChangedItem]

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "What changed", caption: "Last 7 days")

                ForEach(items) { item in
                    HStack(alignment: .top, spacing: Theme.Spacing.md) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.label)
                                .font(Theme.Font.title)
                                .foregroundStyle(Theme.Color.textPrimary)
                            Text(item.detail)
                                .font(Theme.Font.label)
                                .foregroundStyle(Theme.Color.textSecondary)
                        }
                        Spacer()
                        DeltaPill(delta: item.delta, label: "Δ")
                    }
                    if item.id != items.last?.id {
                        Divider().background(Theme.Color.border)
                    }
                }
            }
        }
    }
}

struct RegionDriversCard: View {
    let drivers: [Driver]

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Drivers", caption: "Ranked contributors to current score")

                ForEach(drivers) { driver in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(Format.directionGlyph(driver.direction))
                                .foregroundStyle(driver.direction == .up ? Theme.Color.high : driver.direction == .down ? Theme.Color.low : Theme.Color.textSecondary)
                            Text(driver.label)
                                .font(Theme.Font.body)
                                .foregroundStyle(Theme.Color.textPrimary)
                            Spacer()
                            Text(Format.impactToBars(driver.impact))
                                .font(Theme.Font.mono)
                                .foregroundStyle(Theme.Color.accent)
                        }
                        Text(driver.evidence)
                            .font(Theme.Font.label)
                            .foregroundStyle(Theme.Color.textMuted)
                    }
                    if driver.id != drivers.last?.id {
                        Divider().background(Theme.Color.border)
                    }
                }
            }
        }
    }
}

struct RegionActionsBar: View {
    let streetView: () -> Void
    let simulator: () -> Void
    let compare: () -> Void

    var body: some View {
        VStack(spacing: Theme.Spacing.sm) {
            Button(action: streetView) {
                HStack(spacing: Theme.Spacing.sm) {
                    Image(systemName: "binoculars.fill")
                        .font(.system(size: 16, weight: .semibold))
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Street view")
                            .font(Theme.Font.title)
                        Text("Apple Look Around · 360° ground level")
                            .font(Theme.Font.monoCaption)
                            .tracking(0.5)
                            .foregroundStyle(Theme.Color.textSecondary)
                    }
                    Spacer()
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(Theme.Color.textSecondary)
                }
                .padding(.vertical, 14)
                .padding(.horizontal, Theme.Spacing.md)
                .background(
                    LinearGradient(
                        colors: [Theme.Color.accent.opacity(0.18), Theme.Color.bgRaised],
                        startPoint: .leading,
                        endPoint: .trailing
                    ),
                    in: RoundedRectangle(cornerRadius: Theme.Radius.md)
                )
                .foregroundStyle(Theme.Color.textPrimary)
                .overlay {
                    RoundedRectangle(cornerRadius: Theme.Radius.md)
                        .stroke(Theme.Color.accent.opacity(0.4), lineWidth: 0.8)
                }
            }

            HStack(spacing: Theme.Spacing.sm) {
                actionTile("Simulator", system: "slider.horizontal.3", action: simulator)
                actionTile("Compare", system: "rectangle.split.2x1", action: compare)
            }
        }
    }

    private func actionTile(_ title: String, system: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 6) {
                Image(systemName: system)
                    .font(.system(size: 16))
                Text(title)
                    .font(Theme.Font.label)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(Theme.Color.bgRaised, in: RoundedRectangle(cornerRadius: Theme.Radius.md))
            .foregroundStyle(Theme.Color.textPrimary)
            .overlay {
                RoundedRectangle(cornerRadius: Theme.Radius.md)
                    .stroke(Theme.Color.border, lineWidth: 0.5)
            }
        }
    }
}

private extension Double {
    var asTier: RiskTier { Format.tierFromScore(self) }
}
