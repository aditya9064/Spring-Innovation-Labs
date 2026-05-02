import SwiftUI

struct LiveTabContainer: View {
    @Environment(APIClient.self) private var api
    @Environment(AppStore.self) private var store

    @State private var events: [LiveEvent] = []
    @State private var loading: Bool = true
    @State private var newIds: Set<String> = []
    @State private var ticker = LiveTicker()
    @State private var refreshing: Bool = false

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    LoadingView(label: "Loading live feed…")
                } else {
                    list
                }
            }
            .navigationTitle("Live")
            .navigationBarTitleDisplayMode(.large)
            .background(Theme.Color.bg)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if store.usingMocks { DemoBadge() }
                }
            }
        }
        .task { await load() }
        .refreshable { await load(force: true) }
        .onAppear {
            ticker.onNewEvent = { event in
                Task { @MainActor in
                    events.insert(event, at: 0)
                    newIds.insert(event.id)
                    Task {
                        try? await Task.sleep(for: .seconds(6))
                        newIds.remove(event.id)
                    }
                }
            }
            if store.usingMocks { ticker.start() }
        }
        .onDisappear { ticker.stop() }
    }

    @ViewBuilder
    private var list: some View {
        if events.isEmpty {
            EmptyStateView(title: "No live events", caption: "Quiet across the city. Pull to refresh.", systemImage: "dot.radiowaves.left.and.right")
        } else {
            List {
                Section {
                    LiveCityBanner(events: events)
                }
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets(top: 0, leading: Theme.Spacing.lg, bottom: Theme.Spacing.md, trailing: Theme.Spacing.lg))

                Section("RECENT EVENTS") {
                    ForEach(events) { event in
                        LiveEventRow(event: event, isNew: newIds.contains(event.id))
                            .listRowBackground(Theme.Color.bgPanel)
                            .listRowSeparatorTint(Theme.Color.border)
                    }
                }
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(Theme.Color.bg)
        }
    }

    private func load(force: Bool = false) async {
        if !force { loading = true }
        let fetched = await api.fetchLiveEvents(geoid: nil, limit: 30)
        await MainActor.run {
            self.events = fetched
            self.loading = false
        }
    }
}

struct LiveCityBanner: View {
    let events: [LiveEvent]

    private var verifiedCount: Int { events.filter { $0.status == .verified }.count }
    private var pendingCount: Int { events.filter { $0.status == .pending }.count }

    var body: some View {
        Card(background: Theme.Color.accent.opacity(0.07)) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    HStack(spacing: 6) {
                        Circle().fill(Theme.Color.accent).frame(width: 8, height: 8)
                        Text("CITY-WIDE PULSE")
                            .font(Theme.Font.monoCaption)
                            .tracking(0.7)
                            .foregroundStyle(Theme.Color.accent)
                    }
                    Spacer()
                    Text("\(events.count) events")
                        .font(Theme.Font.mono)
                        .foregroundStyle(Theme.Color.textSecondary)
                }

                HStack(spacing: Theme.Spacing.lg) {
                    pulseStat(label: "VERIFIED", value: "\(verifiedCount)", tint: Theme.Color.low)
                    pulseStat(label: "PENDING", value: "\(pendingCount)", tint: Theme.Color.elevated)
                    pulseStat(label: "UNVERIFIED", value: "\(events.count - verifiedCount - pendingCount)", tint: Theme.Color.textSecondary)
                }
            }
        }
    }

    private func pulseStat(label: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(Theme.Font.monoCaption)
                .foregroundStyle(Theme.Color.textMuted)
                .tracking(0.6)
            Text(value)
                .font(Theme.Font.monoNumber)
                .foregroundStyle(tint)
                .monospacedDigit()
        }
    }
}

struct LiveEventRow: View {
    let event: LiveEvent
    let isNew: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                sourceTag
                statusTag
                Spacer()
                if isNew {
                    Text("NEW")
                        .font(Theme.Font.monoCaption)
                        .tracking(0.7)
                        .foregroundStyle(Theme.Color.accent)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(Theme.Color.accent.opacity(0.15), in: Capsule())
                }
                Text(Format.timeAgo(event.occurredAt))
                    .font(Theme.Font.monoCaption)
                    .foregroundStyle(Theme.Color.textMuted)
            }
            Text(event.summary)
                .font(Theme.Font.body)
                .foregroundStyle(Theme.Color.textPrimary)
            HStack {
                Text(event.regionName)
                    .font(Theme.Font.label)
                    .foregroundStyle(Theme.Color.textSecondary)
                Text("·")
                    .foregroundStyle(Theme.Color.textMuted)
                Text(event.category.uppercased())
                    .font(Theme.Font.monoCaption)
                    .foregroundStyle(Theme.Color.textMuted)
                    .tracking(0.6)
                Spacer()
                Text(Format.percent(event.confidence))
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
        .padding(.vertical, 6)
    }

    private var sourceTag: some View {
        let label: String
        let tint: Color
        switch event.source {
        case .dispatch_911: label = "911"; tint = Theme.Color.critical
        case .fire: label = "FIRE"; tint = Theme.Color.high
        case .sensor: label = "SENSOR"; tint = Theme.Color.elevated
        case .social: label = "SOCIAL"; tint = Theme.Color.moderate
        case .news: label = "NEWS"; tint = Theme.Color.accent
        case .crowdsource: label = "CROWD"; tint = Theme.Color.low
        }
        return Text(label)
            .font(Theme.Font.monoCaption)
            .tracking(0.7)
            .foregroundStyle(tint)
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(tint.opacity(0.15), in: Capsule())
    }

    private var statusTag: some View {
        let tint: Color
        switch event.status {
        case .verified: tint = Theme.Color.low
        case .pending: tint = Theme.Color.elevated
        case .unverified: tint = Theme.Color.textMuted
        }
        return Text(event.status.rawValue.uppercased())
            .font(Theme.Font.monoCaption)
            .tracking(0.6)
            .foregroundStyle(tint)
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(tint.opacity(0.12), in: Capsule())
    }
}
