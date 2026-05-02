import SwiftUI

struct BlindSpotsView: View {
    @Environment(APIClient.self) private var api
    @Environment(AppStore.self) private var store
    @State private var entries: [BlindSpots.Entry] = []
    @State private var loaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                Card(background: Theme.Color.high.opacity(0.08)) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Where the data may be wrong")
                            .font(Theme.Font.titleLarge)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Text("Tracts flagged for high underreporting risk or weak coverage. Reported scores in these tracts may be conservative — verify before confident decisions.")
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textSecondary)
                    }
                }

                if entries.isEmpty {
                    EmptyStateView(title: "No blind spots flagged", caption: "Coverage looks healthy across the city.", systemImage: "eye")
                } else {
                    ForEach(entries) { entry in
                        Card {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text(entry.name)
                                        .font(Theme.Font.title)
                                        .foregroundStyle(Theme.Color.textPrimary)
                                    Spacer()
                                    Text("UR \(Format.percent(entry.underreportingRisk))")
                                        .font(Theme.Font.mono)
                                        .foregroundStyle(Theme.Color.high)
                                }
                                Text(entry.reason)
                                    .font(Theme.Font.body)
                                    .foregroundStyle(Theme.Color.textSecondary)
                                HStack {
                                    Text("COVERAGE \(Format.percent(entry.coverageScore))")
                                        .font(Theme.Font.monoCaption)
                                        .tracking(0.6)
                                        .foregroundStyle(Theme.Color.textMuted)
                                    Spacer()
                                }
                            }
                        }
                    }
                }
            }
            .padding(Theme.Spacing.lg)
        }
        .background(Theme.Color.bg)
        .navigationTitle("Blind Spots")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if loaded { return }
            // Pull current city's loaded scores so blind-spots reflect live data
            // when the API is reachable. Falls back to MockData when offline.
            let scores = await api.fetchScores(city: store.city)
            entries = BlindSpots.compute(from: scores.isEmpty ? MockData.tracts : scores)
            loaded = true
        }
    }
}
