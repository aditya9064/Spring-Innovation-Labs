import SwiftUI

struct MoreTabContainer: View {
    @Environment(AppStore.self) private var store
    @Environment(APIClient.self) private var api
    @State private var allTracts: [TractScore] = []

    private var watchlistTracts: [TractScore] {
        allTracts.filter { store.watchlist.contains($0.geoid) }
    }

    var body: some View {
        NavigationStack {
            List {
                if store.usingMocks {
                    Section {
                        HStack {
                            DemoBadge()
                            Spacer()
                            NavigationLink("Settings") { SettingsView() }
                                .font(Theme.Font.label)
                        }
                        .listRowBackground(Theme.Color.bgPanel)
                    }
                }

                Section("WATCHLIST") {
                    if watchlistTracts.isEmpty {
                        Text("Star regions from the map to add them here.")
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textMuted)
                            .listRowBackground(Theme.Color.bgPanel)
                    } else {
                        ForEach(watchlistTracts) { tract in
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
                            .listRowBackground(Theme.Color.bgPanel)
                        }
                    }
                }

                Section("DECISION SUPPORT") {
                    NavigationLink { ComparePickerWrapper() } label: {
                        Label("Compare regions", systemImage: "rectangle.split.2x1")
                    }
                    NavigationLink { AuditListView() } label: {
                        Label("Audit Trail", systemImage: "checkmark.seal")
                    }
                    NavigationLink { ChallengeListView() } label: {
                        Label("Challenge Mode", systemImage: "exclamationmark.bubble")
                    }
                    NavigationLink { BlindSpotsView() } label: {
                        Label("Blind Spots", systemImage: "eye.trianglebadge.exclamationmark")
                    }
                }
                .listRowBackground(Theme.Color.bgPanel)

                Section("SUPPORT") {
                    NavigationLink { ChatView() } label: {
                        Label("Ask the AI assistant", systemImage: "sparkles")
                    }
                    NavigationLink { SettingsView() } label: {
                        Label("Settings", systemImage: "gearshape")
                    }
                }
                .listRowBackground(Theme.Color.bgPanel)
            }
            .scrollContentBackground(.hidden)
            .background(Theme.Color.bg)
            .navigationTitle("More")
            .navigationBarTitleDisplayMode(.large)
        }
        .task {
            allTracts = await api.fetchScores(city: store.city)
        }
    }
}

struct ComparePickerWrapper: View {
    var body: some View {
        ComparePickerView()
    }
}
