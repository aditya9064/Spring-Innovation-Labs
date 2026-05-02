import SwiftUI

struct ReportsTabContainer: View {
    @Environment(APIClient.self) private var api
    @Environment(AppStore.self) private var store
    @State private var tracts: [TractScore] = []
    @State private var query: String = ""
    @State private var loading: Bool = true

    private var filtered: [TractScore] {
        let base = query.isEmpty
            ? tracts
            : tracts.filter { $0.name.localizedCaseInsensitiveContains(query) || $0.geoid.contains(query) }
        return base.sorted { $0.score > $1.score }
    }

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    LoadingView(label: "Loading reports…")
                } else {
                    list
                }
            }
            .navigationTitle("Reports")
            .navigationBarTitleDisplayMode(.large)
            .background(Theme.Color.bg)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if store.usingMocks { DemoBadge() }
                }
            }
        }
        .task { await load() }
    }

    @ViewBuilder
    private var list: some View {
        List {
            ForEach(filtered) { tract in
                NavigationLink {
                    ReportDetailView(geoid: tract.geoid)
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
        }
        .scrollContentBackground(.hidden)
        .background(Theme.Color.bg)
        .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search regions")
    }

    private func load() async {
        loading = true
        let fetched = await api.fetchScores(city: store.city)
        await MainActor.run { self.tracts = fetched; self.loading = false }
    }
}

struct ReportDetailView: View {
    let geoid: String
    @Environment(APIClient.self) private var api
    @State private var report: ReportSummary?
    @State private var loading: Bool = true
    @State private var pdfURL: URL?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                if loading {
                    LoadingView(label: "Generating report…")
                        .frame(height: 280)
                } else if let report {
                    header(report)
                    section("Executive summary", body: report.executiveSummary)
                    section("Risk narrative", body: report.riskNarrative)
                    section("Trust notes", body: report.trustNotes)
                    drivers(report)
                    peers(report)
                    challenges(report)
                    if let pdfURL {
                        ShareLink(item: pdfURL) {
                            Label("Share PDF", systemImage: "square.and.arrow.up")
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(Theme.Color.accent, in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
                                .foregroundStyle(Theme.Color.bg)
                        }
                    } else {
                        PrimaryButton(title: "Export PDF", systemImage: "doc.richtext") {
                            generatePDF(from: report)
                        }
                    }
                }
            }
            .padding(Theme.Spacing.lg)
        }
        .background(Theme.Color.bg)
        .navigationTitle(report?.name ?? "Report")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func header(_ report: ReportSummary) -> some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                HStack {
                    Text(report.name)
                        .font(Theme.Font.titleLarge)
                        .foregroundStyle(Theme.Color.textPrimary)
                    Spacer()
                    TierPill(tier: report.tier, size: .md)
                }
                Text("Generated \(Format.dateTime(report.generatedAt))")
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.textMuted)
            }
        }
    }

    private func section(_ title: String, body: String) -> some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                SectionHeader(title: title)
                Text(body)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)
            }
        }
    }

    private func drivers(_ report: ReportSummary) -> some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Drivers")
                ForEach(report.drivers) { d in
                    HStack(alignment: .top, spacing: 10) {
                        Text(Format.directionGlyph(d.direction))
                            .foregroundStyle(d.direction == .up ? Theme.Color.high : d.direction == .down ? Theme.Color.low : Theme.Color.textSecondary)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(d.label)
                                .font(Theme.Font.body)
                                .foregroundStyle(Theme.Color.textPrimary)
                            Text(d.evidence)
                                .font(Theme.Font.label)
                                .foregroundStyle(Theme.Color.textMuted)
                        }
                        Spacer()
                        Text(Format.impactToBars(d.impact))
                            .font(Theme.Font.mono)
                            .foregroundStyle(Theme.Color.accent)
                    }
                }
            }
        }
    }

    private func peers(_ report: ReportSummary) -> some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Peer comparison", caption: "Other tracts in the same tier")
                ForEach(report.peerCompare, id: \.geoid) { peer in
                    HStack {
                        Text(peer.name)
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Spacer()
                        TierPill(tier: peer.tier, size: .sm, withScore: peer.score)
                    }
                }
            }
        }
    }

    private func challenges(_ report: ReportSummary) -> some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                SectionHeader(title: "Challenges & notes")
                ForEach(report.challenges, id: \.self) { c in
                    Text("· \(c)")
                        .font(Theme.Font.body)
                        .foregroundStyle(Theme.Color.textSecondary)
                }
            }
        }
    }

    private func load() async {
        loading = true
        let fetched = await api.fetchReport(geoid: geoid)
        await MainActor.run { self.report = fetched; self.loading = false }
    }

    private func generatePDF(from report: ReportSummary) {
        let url = PDFRenderer.render(report: report)
        pdfURL = url
    }
}
