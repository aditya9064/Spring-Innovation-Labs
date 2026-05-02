import SwiftUI

struct ChallengeListView: View {
    @Environment(ChallengeStore.self) private var store
    @State private var creating: Bool = false

    private var stats: (open: Int, inReview: Int, total: Int) {
        let open = store.entries.filter { $0.status == .pending }.count
        let inReview = store.entries.filter { $0.status == .in_review }.count
        return (open, inReview, store.entries.count)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                statsCard
                if store.entries.isEmpty {
                    EmptyStateView(title: "No challenges", caption: "Submit a challenge to data, model, decision, or scope.", systemImage: "exclamationmark.bubble")
                } else {
                    ForEach(store.entries) { record in
                        entryCard(record)
                    }
                }
            }
            .padding(Theme.Spacing.lg)
        }
        .background(Theme.Color.bg)
        .navigationTitle("Challenge Mode")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { creating = true } label: { Image(systemName: "plus") }
            }
        }
        .sheet(isPresented: $creating) {
            ChallengeNewView()
        }
    }

    private var statsCard: some View {
        Card {
            HStack(spacing: Theme.Spacing.lg) {
                statColumn("Total", "\(stats.total)", Theme.Color.accent)
                statColumn("Pending", "\(stats.open)", Theme.Color.elevated)
                statColumn("In review", "\(stats.inReview)", Theme.Color.moderate)
            }
        }
    }

    private func statColumn(_ label: String, _ value: String, _ tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(Theme.Font.monoCaption)
                .tracking(0.6)
                .foregroundStyle(Theme.Color.textMuted)
            Text(value)
                .font(Theme.Font.monoNumber)
                .foregroundStyle(tint)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func entryCard(_ record: ChallengeRecord) -> some View {
        Card {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(record.regionName)
                            .font(Theme.Font.title)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Text("\(record.challengerName) · \(Format.timeAgo(record.createdAt))")
                            .font(Theme.Font.label)
                            .foregroundStyle(Theme.Color.textSecondary)
                    }
                    Spacer()
                    statusPill(record.status)
                }
                HStack {
                    Text(record.challengeType.displayName.uppercased())
                        .font(Theme.Font.monoCaption)
                        .tracking(0.7)
                        .foregroundStyle(Theme.Color.accent)
                        .padding(.horizontal, 8).padding(.vertical, 3)
                        .background(Theme.Color.accent.opacity(0.12), in: Capsule())
                    Spacer()
                    DeltaPill(delta: record.proposedAdjustment, label: "Adj.")
                }
                Text(record.evidence)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)
            }
        }
    }

    private func statusPill(_ status: ChallengeRecord.Status) -> some View {
        let tint: Color
        switch status {
        case .pending: tint = Theme.Color.elevated
        case .approved: tint = Theme.Color.low
        case .rejected: tint = Theme.Color.critical
        case .in_review: tint = Theme.Color.moderate
        }
        return Text(status.displayName.uppercased())
            .font(Theme.Font.monoCaption)
            .tracking(0.7)
            .foregroundStyle(tint)
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(tint.opacity(0.12), in: Capsule())
    }
}

struct ChallengeNewView: View {
    var prefillPackage: TractRiskPackage? = nil

    @Environment(ChallengeStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var regionName: String = ""
    @State private var geoid: String = ""
    @State private var challengerName: String = ""
    @State private var challengeType: ChallengeRecord.ChallengeType = .data
    @State private var evidence: String = ""
    @State private var proposedAdjustment: Double = 0

    var body: some View {
        NavigationStack {
            Form {
                Section("REGION") {
                    TextField("Region name", text: $regionName)
                    TextField("GEOID", text: $geoid)
                }
                Section("CHALLENGER") {
                    TextField("Your name", text: $challengerName)
                    Picker("Challenge type", selection: $challengeType) {
                        ForEach(ChallengeRecord.ChallengeType.allCases, id: \.self) { type in
                            Text(type.displayName).tag(type)
                        }
                    }
                }
                Section("EVIDENCE") {
                    TextField("What's wrong, and how do you know?", text: $evidence, axis: .vertical)
                        .lineLimit(4...8)
                }
                Section("PROPOSED ADJUSTMENT") {
                    HStack {
                        Text(Format.delta(proposedAdjustment))
                            .font(Theme.Font.monoNumber)
                            .foregroundStyle(proposedAdjustment > 0 ? Theme.Color.high : proposedAdjustment < 0 ? Theme.Color.low : Theme.Color.textSecondary)
                            .monospacedDigit()
                            .frame(width: 80, alignment: .leading)
                        Slider(value: $proposedAdjustment, in: -20...20, step: 0.5)
                            .tint(Theme.Color.accent)
                    }
                    Text("Proposed score adjustment in points (range −20 to +20).")
                        .font(Theme.Font.label)
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
            .navigationTitle("New challenge")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Submit") { submit() }
                        .disabled(!canSubmit)
                        .bold()
                }
            }
            .onAppear {
                if let pkg = prefillPackage {
                    regionName = pkg.name
                    geoid = pkg.geoid
                }
            }
        }
    }

    private var canSubmit: Bool {
        !regionName.isEmpty && !challengerName.isEmpty && !evidence.isEmpty
    }

    private func submit() {
        let record = ChallengeRecord(
            id: UUID().uuidString,
            geoid: geoid,
            regionName: regionName,
            challengerName: challengerName,
            challengeType: challengeType,
            evidence: evidence,
            proposedAdjustment: proposedAdjustment,
            status: .pending,
            createdAt: Date()
        )
        store.add(record)
        dismiss()
    }
}
