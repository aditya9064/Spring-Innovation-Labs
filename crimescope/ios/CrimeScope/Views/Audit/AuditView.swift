import SwiftUI

struct AuditListView: View {
    @Environment(AuditStore.self) private var auditStore
    @State private var creating: Bool = false

    private var stats: (total: Int, overrides: Int, lastWeek: Int) {
        let total = auditStore.entries.count
        let overrides = auditStore.entries.filter { $0.overrodeMl }.count
        let cutoff = Date().addingTimeInterval(-86400 * 7)
        let lastWeek = auditStore.entries.filter { $0.createdAt > cutoff }.count
        return (total, overrides, lastWeek)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                statsCard
                if auditStore.entries.isEmpty {
                    EmptyStateView(title: "No audit entries", caption: "Decisions you log will appear here.", systemImage: "checkmark.seal")
                        .padding(.top, Theme.Spacing.xl)
                } else {
                    ForEach(auditStore.entries) { record in
                        entryCard(record)
                    }
                }
            }
            .padding(Theme.Spacing.lg)
        }
        .background(Theme.Color.bg)
        .navigationTitle("Audit Trail")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { creating = true } label: { Image(systemName: "plus") }
            }
        }
        .sheet(isPresented: $creating) {
            AuditNewView()
        }
    }

    private var statsCard: some View {
        Card {
            HStack(spacing: Theme.Spacing.lg) {
                statColumn(label: "Total", value: "\(stats.total)", tint: Theme.Color.accent)
                statColumn(label: "Overrides", value: "\(stats.overrides)", tint: Theme.Color.high)
                statColumn(label: "Last 7d", value: "\(stats.lastWeek)", tint: Theme.Color.low)
            }
        }
    }

    private func statColumn(label: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(Theme.Font.monoCaption)
                .foregroundStyle(Theme.Color.textMuted)
                .tracking(0.7)
            Text(value)
                .font(Theme.Font.monoNumber)
                .foregroundStyle(tint)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func entryCard(_ record: AuditRecord) -> some View {
        Card {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(record.regionName)
                            .font(Theme.Font.title)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Text("\(record.persona.displayName) · \(Format.timeAgo(record.createdAt))")
                            .font(Theme.Font.label)
                            .foregroundStyle(Theme.Color.textSecondary)
                    }
                    Spacer()
                    TierPill(tier: record.riskTier, size: .sm, withScore: record.riskScore)
                }
                Text(record.decision)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)
                Text(record.rationale)
                    .font(Theme.Font.label)
                    .foregroundStyle(Theme.Color.textSecondary)
                if record.overrodeMl {
                    Text("OVERRODE ML")
                        .font(Theme.Font.monoCaption)
                        .tracking(0.7)
                        .foregroundStyle(Theme.Color.high)
                        .padding(.horizontal, 8).padding(.vertical, 3)
                        .background(Theme.Color.high.opacity(0.15), in: Capsule())
                }
            }
        }
    }
}

struct AuditNewView: View {
    var prefillPackage: TractRiskPackage? = nil

    @Environment(AuditStore.self) private var auditStore
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var regionName: String = ""
    @State private var geoid: String = ""
    @State private var score: String = ""
    @State private var decision: String = ""
    @State private var rationale: String = ""
    @State private var overrodeMl: Bool = false

    var body: some View {
        NavigationStack {
            Form {
                Section("REGION") {
                    TextField("Region name", text: $regionName)
                    TextField("GEOID", text: $geoid)
                        .keyboardType(.numbersAndPunctuation)
                    TextField("Risk score (0-100)", text: $score)
                        .keyboardType(.decimalPad)
                }
                Section("DECISION") {
                    TextField("Decision", text: $decision)
                    TextField("Rationale", text: $rationale, axis: .vertical)
                        .lineLimit(3...6)
                    Toggle("Overrode ML recommendation", isOn: $overrodeMl)
                }
            }
            .navigationTitle("New audit entry")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Save") { save() }
                        .disabled(!canSave)
                        .bold()
                }
            }
            .onAppear {
                if let pkg = prefillPackage {
                    regionName = pkg.name
                    geoid = pkg.geoid
                    score = Format.score(pkg.scores.overall)
                    decision = pkg.personaDecisions.first(where: { $0.persona == store.persona })?.recommendation ?? ""
                }
            }
        }
    }

    private var canSave: Bool {
        !regionName.isEmpty && !geoid.isEmpty && Double(score) != nil && !decision.isEmpty
    }

    private func save() {
        guard let numScore = Double(score) else { return }
        let record = AuditRecord(
            id: UUID().uuidString,
            geoid: geoid,
            regionName: regionName,
            persona: store.persona,
            riskScore: numScore,
            riskTier: Format.tierFromScore(numScore),
            decision: decision,
            rationale: rationale,
            overrodeMl: overrodeMl,
            createdAt: Date()
        )
        auditStore.add(record)
        dismiss()
    }
}
