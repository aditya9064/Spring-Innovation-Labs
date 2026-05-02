import SwiftUI

struct SimulatorView: View {
    let pkg: TractRiskPackage
    @Environment(APIClient.self) private var api
    @Environment(AuditStore.self) private var auditStore
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var values: [String: Double] = [:]
    @State private var result: SimulationResult?
    @State private var loading: Bool = false
    @State private var loggedToAudit: Bool = false

    private var interventions: [Intervention] { api.interventions() }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                    summaryCard
                    interventionsCard
                    if let result {
                        resultCard(result)
                    }
                    if loggedToAudit {
                        Card(background: Theme.Color.low.opacity(0.12)) {
                            HStack(spacing: 8) {
                                Image(systemName: "checkmark.seal.fill")
                                    .foregroundStyle(Theme.Color.low)
                                Text("Logged to audit trail")
                                    .font(Theme.Font.body)
                                    .foregroundStyle(Theme.Color.textPrimary)
                            }
                        }
                    }
                }
                .padding(Theme.Spacing.lg)
            }
            .background(Theme.Color.bg)
            .navigationTitle("Simulator")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                }
            }
            .task {
                if values.isEmpty {
                    for i in interventions { values[i.id] = i.defaultValue }
                    await runSimulation()
                }
            }
        }
    }

    private var summaryCard: some View {
        Card {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(pkg.name)
                        .font(Theme.Font.titleLarge)
                        .foregroundStyle(Theme.Color.textPrimary)
                    Spacer()
                    TierPill(tier: Format.tierFromScore(pkg.scores.overall), size: .md, withScore: pkg.scores.overall)
                }
                Text("Adjust intervention intensity to see projected impact on the score-of-record.")
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
    }

    private var interventionsCard: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                SectionHeader(title: "Interventions")
                ForEach(interventions) { intervention in
                    if let binding = binding(for: intervention.id) {
                        InterventionSlider(
                            intervention: intervention,
                            value: binding
                        )
                    }
                }
                PrimaryButton(title: loading ? "Simulating…" : "Run simulation", systemImage: "play.fill") {
                    Task { await runSimulation() }
                }
            }
        }
    }

    private func resultCard(_ result: SimulationResult) -> some View {
        Card(background: Theme.Color.accent.opacity(0.06)) {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Projection")

                HStack(spacing: Theme.Spacing.lg) {
                    ScoreNumber(value: result.baselineScore, label: "Baseline", size: .md)
                    Image(systemName: "arrow.right")
                        .foregroundStyle(Theme.Color.textMuted)
                    ScoreNumber(value: result.simulatedScore, label: "Projected", size: .md, tint: Theme.Color.accent)
                    Spacer()
                    TierPill(tier: result.projectedTier, size: .md)
                }

                Text(result.narrative)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)

                Divider().background(Theme.Color.border)

                Text("BREAKDOWN")
                    .font(Theme.Font.monoCaption)
                    .tracking(0.6)
                    .foregroundStyle(Theme.Color.textMuted)
                ForEach(result.breakdown) { row in
                    HStack {
                        Text(row.label)
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Spacer()
                        DeltaPill(delta: row.delta)
                    }
                }

                if !loggedToAudit {
                    SecondaryButton(title: "Log result to audit trail", systemImage: "tray.and.arrow.down") {
                        logToAudit(result)
                    }
                }
            }
        }
    }

    private func binding(for id: String) -> Binding<Double>? {
        guard values[id] != nil else { return nil }
        return Binding(
            get: { values[id] ?? 0 },
            set: { values[id] = $0 }
        )
    }

    private func runSimulation() async {
        loading = true
        let r = await api.simulate(geoid: pkg.geoid, values: values)
        await MainActor.run {
            self.result = r
            self.loading = false
        }
    }

    private func logToAudit(_ result: SimulationResult) {
        let record = AuditRecord(
            id: UUID().uuidString,
            geoid: pkg.geoid,
            regionName: pkg.name,
            persona: store.persona,
            riskScore: result.simulatedScore,
            riskTier: result.projectedTier,
            decision: "Simulated intervention bundle",
            rationale: result.narrative,
            overrodeMl: false,
            createdAt: Date()
        )
        auditStore.add(record)
        loggedToAudit = true
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
    }
}
