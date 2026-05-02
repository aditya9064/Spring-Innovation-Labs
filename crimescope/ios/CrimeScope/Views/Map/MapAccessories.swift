import SwiftUI

struct KpiStrip: View {
    let tracts: [TractScore]

    private var critical: Int { tracts.filter { $0.tier == .critical }.count }
    private var high: Int { tracts.filter { $0.tier == .high }.count }
    private var avg: Double {
        guard !tracts.isEmpty else { return 0 }
        return tracts.map(\.score).reduce(0, +) / Double(tracts.count)
    }

    var body: some View {
        HStack(spacing: Theme.Spacing.sm) {
            kpi("REGIONS", value: "\(tracts.count)", color: Theme.Color.textPrimary)
            kpi("CRITICAL", value: "\(critical)", color: Theme.Color.critical)
            kpi("HIGH", value: "\(high)", color: Theme.Color.high)
            kpi("AVG", value: Format.score(avg), color: Theme.Color.accent)
        }
    }

    private func kpi(_ label: String, value: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(Theme.Font.monoCaption)
                .tracking(0.6)
                .foregroundStyle(Theme.Color.textMuted)
            Text(value)
                .font(Theme.Font.monoNumber)
                .foregroundStyle(color)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Theme.Color.bgPanel.opacity(0.92), in: RoundedRectangle(cornerRadius: Theme.Radius.md))
    }
}

struct TierFilterBar: View {
    @Binding var allowed: Set<RiskTier>

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(RiskTier.allCases, id: \.self) { tier in
                    chip(tier)
                }
                Button("Reset") {
                    allowed = Set(RiskTier.allCases)
                }
                .font(Theme.Font.label)
                .padding(.horizontal, 10).padding(.vertical, 6)
                .foregroundStyle(Theme.Color.textSecondary)
            }
            .padding(.trailing, Theme.Spacing.lg)
        }
    }

    private func chip(_ tier: RiskTier) -> some View {
        let on = allowed.contains(tier)
        return Button {
            if on { allowed.remove(tier) } else { allowed.insert(tier) }
        } label: {
            HStack(spacing: 6) {
                Circle().fill(tier.color).frame(width: 6, height: 6)
                Text(tier.rawValue.uppercased())
                    .font(Theme.Font.monoCaption)
                    .tracking(0.6)
                    .foregroundStyle(on ? tier.color : Theme.Color.textMuted)
            }
            .padding(.horizontal, 10).padding(.vertical, 6)
            .background(
                on ? tier.color.opacity(0.18) : Theme.Color.bgPanel.opacity(0.85),
                in: Capsule()
            )
            .overlay {
                Capsule().stroke(on ? tier.color.opacity(0.4) : Theme.Color.border, lineWidth: 0.5)
            }
        }
    }
}

struct MapLegend: View {
    var body: some View {
        HStack(spacing: 10) {
            ForEach(RiskTier.allCases, id: \.self) { tier in
                HStack(spacing: 4) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(tier.color)
                        .frame(width: 10, height: 6)
                    Text(tier.rawValue.uppercased())
                        .font(Theme.Font.monoCaption)
                        .tracking(0.5)
                        .foregroundStyle(Theme.Color.textSecondary)
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Theme.Color.bgPanel.opacity(0.85), in: RoundedRectangle(cornerRadius: Theme.Radius.md))
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct TractSearchSheet: View {
    let tracts: [TractScore]
    let onSelect: (TractScore) -> Void
    @State private var query: String = ""
    @Environment(\.dismiss) private var dismiss

    private var filtered: [TractScore] {
        if query.isEmpty { return tracts.sorted { $0.score > $1.score } }
        return tracts.filter {
            $0.name.localizedCaseInsensitiveContains(query) ||
            $0.geoid.contains(query)
        }
    }

    var body: some View {
        NavigationStack {
            List {
                ForEach(filtered) { t in
                    Button { onSelect(t) } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(t.name)
                                    .font(Theme.Font.title)
                                    .foregroundStyle(Theme.Color.textPrimary)
                                Text(Format.shortGeoid(t.geoid))
                                    .font(Theme.Font.mono)
                                    .foregroundStyle(Theme.Color.textMuted)
                            }
                            Spacer()
                            TierPill(tier: t.tier, size: .sm, withScore: t.score)
                        }
                        .contentShape(Rectangle())
                    }
                    .listRowBackground(Theme.Color.bgPanel)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.Color.bg)
            .navigationTitle("Find region")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Name or GEOID")
        }
    }
}
