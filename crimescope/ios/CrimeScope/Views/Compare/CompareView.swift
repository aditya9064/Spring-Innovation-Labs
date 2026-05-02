import SwiftUI

struct ComparePickerView: View {
    var left: TractScore? = nil
    @Environment(APIClient.self) private var api
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var tracts: [TractScore] = []
    @State private var leftSelection: TractScore?
    @State private var rightSelection: TractScore?
    @State private var query: String = ""

    private var filtered: [TractScore] {
        if query.isEmpty { return tracts }
        return tracts.filter {
            $0.name.localizedCaseInsensitiveContains(query) ||
            $0.geoid.contains(query)
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Theme.Color.bg.ignoresSafeArea()
                VStack(spacing: 0) {
                    selectionBar
                        .padding(Theme.Spacing.lg)
                        .background(Theme.Color.bgPanel)

                    List(filtered) { tract in
                        Button {
                            handleSelect(tract)
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(tract.name)
                                        .font(Theme.Font.title)
                                        .foregroundStyle(Theme.Color.textPrimary)
                                    Text(Format.shortGeoid(tract.geoid))
                                        .font(Theme.Font.mono)
                                        .foregroundStyle(Theme.Color.textMuted)
                                }
                                Spacer()
                                TierPill(tier: tract.tier, size: .sm, withScore: tract.score)
                            }
                        }
                        .listRowBackground(Theme.Color.bgPanel)
                    }
                    .scrollContentBackground(.hidden)
                    .background(Theme.Color.bg)
                }

                if let l = leftSelection, let r = rightSelection {
                    VStack {
                        Spacer()
                        Button {
                            // open compare detail via navigation
                            // handled by NavigationLink push
                        } label: {
                            NavigationLink {
                                CompareDetailView(left: l, right: r)
                            } label: {
                                Text("Compare \(l.name) vs \(r.name)")
                                    .font(Theme.Font.title)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                                    .background(Theme.Color.accent, in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
                                    .foregroundStyle(Theme.Color.bg)
                            }
                        }
                        .padding(Theme.Spacing.lg)
                    }
                }
            }
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Find region")
            .navigationTitle("Compare")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .task {
            tracts = await api.fetchScores(city: store.city)
            if let preset = left { leftSelection = preset }
        }
    }

    private var selectionBar: some View {
        HStack(spacing: Theme.Spacing.md) {
            slot(label: "LEFT", tract: leftSelection)
            Image(systemName: "arrow.left.and.right")
                .foregroundStyle(Theme.Color.textMuted)
            slot(label: "RIGHT", tract: rightSelection)
        }
    }

    private func slot(label: String, tract: TractScore?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(Theme.Font.monoCaption)
                .tracking(0.7)
                .foregroundStyle(Theme.Color.textMuted)
            if let tract {
                Text(tract.name)
                    .font(Theme.Font.title)
                    .foregroundStyle(Theme.Color.textPrimary)
                TierPill(tier: tract.tier, size: .sm, withScore: tract.score)
            } else {
                Text("Tap a region")
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textMuted)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(Theme.Spacing.md)
        .background(Theme.Color.bgRaised, in: RoundedRectangle(cornerRadius: Theme.Radius.md))
    }

    private func handleSelect(_ tract: TractScore) {
        if leftSelection == nil {
            leftSelection = tract
        } else if rightSelection == nil, tract.geoid != leftSelection?.geoid {
            rightSelection = tract
        } else {
            leftSelection = tract
            rightSelection = nil
        }
    }
}

struct CompareDetailView: View {
    let left: TractScore
    let right: TractScore
    @Environment(APIClient.self) private var api
    @State private var leftSnap: CompareSnapshot?
    @State private var rightSnap: CompareSnapshot?
    @State private var loadState: LoadState = .loading

    private enum LoadState { case loading, loaded, failed }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                if let l = leftSnap, let r = rightSnap {
                    summary(l, r)
                    sideBySide(l, r)
                    recommendations(l, r)
                } else if loadState == .failed {
                    EmptyStateView(
                        title: "Comparison unavailable",
                        caption: "We couldn't load comparison data for these regions. Check your connection or try again.",
                        systemImage: "exclamationmark.triangle"
                    )
                    .frame(maxWidth: .infinity)
                    Button {
                        Task { await load() }
                    } label: {
                        Text("Retry")
                            .font(Theme.Font.title)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(Theme.Color.accent, in: RoundedRectangle(cornerRadius: Theme.Radius.md))
                            .foregroundStyle(Theme.Color.bg)
                    }
                } else {
                    LoadingView(label: "Loading comparison…")
                        .frame(height: 240)
                }
            }
            .padding(Theme.Spacing.lg)
        }
        .background(Theme.Color.bg)
        .navigationTitle("Compare")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        loadState = .loading
        if let result = await api.fetchCompare(left: left.geoid, right: right.geoid) {
            leftSnap = result.0
            rightSnap = result.1
            loadState = .loaded
        } else {
            loadState = .failed
        }
    }

    private func summary(_ l: CompareSnapshot, _ r: CompareSnapshot) -> some View {
        Card(background: Theme.Color.accent.opacity(0.08)) {
            VStack(alignment: .leading, spacing: 6) {
                SectionHeader(title: "AI summary")
                Text(api.aiSummary(for: l, vs: r))
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)
            }
        }
    }

    private func sideBySide(_ l: CompareSnapshot, _ r: CompareSnapshot) -> some View {
        Card {
            VStack(spacing: Theme.Spacing.md) {
                HStack(alignment: .top, spacing: Theme.Spacing.lg) {
                    column(snap: l)
                    Divider().background(Theme.Color.border)
                    column(snap: r)
                }
            }
        }
    }

    private func column(snap: CompareSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(snap.name)
                .font(Theme.Font.title)
                .foregroundStyle(Theme.Color.textPrimary)
            TierPill(tier: snap.tier, size: .md, withScore: snap.score)
            stat("Baseline", Format.score(snap.baselineScore))
            stat("ML-adjusted", Format.score(snap.mlScore))
            stat("Live Δ", Format.delta(snap.liveDelta))
            stat("Confidence", Format.percent(snap.trust.confidence))
            stat("Underreporting", Format.percent(snap.trust.underreportingRisk))
            VStack(alignment: .leading, spacing: 4) {
                Text("TOP DRIVERS").font(Theme.Font.monoCaption).foregroundStyle(Theme.Color.textMuted).tracking(0.6)
                ForEach(snap.topDrivers) { d in
                    Text("· \(d.label)")
                        .font(Theme.Font.label)
                        .foregroundStyle(Theme.Color.textSecondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func stat(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label.uppercased())
                .font(Theme.Font.monoCaption)
                .tracking(0.6)
                .foregroundStyle(Theme.Color.textMuted)
            Spacer()
            Text(value)
                .font(Theme.Font.mono)
                .foregroundStyle(Theme.Color.textPrimary)
        }
    }

    private func recommendations(_ l: CompareSnapshot, _ r: CompareSnapshot) -> some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Recommendations")
                rec(l)
                Divider().background(Theme.Color.border)
                rec(r)
            }
        }
    }

    private func rec(_ snap: CompareSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(snap.name).font(Theme.Font.title).foregroundStyle(Theme.Color.textPrimary)
            Text(snap.recommendation).font(Theme.Font.body).foregroundStyle(Theme.Color.textSecondary)
        }
    }
}
