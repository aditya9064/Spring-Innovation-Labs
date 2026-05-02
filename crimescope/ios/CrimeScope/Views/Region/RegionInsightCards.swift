import Charts
import SwiftUI

// MARK: - Trend + 30-day forecast card

struct RegionTrendCard: View {
    let geoid: String
    let regionName: String
    @Environment(APIClient.self) private var api

    @State private var trend: RegionTrend?
    @State private var loading = true
    @State private var failed = false

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Trend · next 30 days", caption: caption)

                if loading {
                    LoadingView(label: "Loading trend…").frame(height: 160)
                } else if let trend {
                    TrendChartContent(trend: trend)
                        .frame(height: 180)

                    expectedRow(trend)

                    Text(trend.method)
                        .font(Theme.Font.monoCaption)
                        .tracking(0.4)
                        .foregroundStyle(Theme.Color.textMuted)
                } else if failed {
                    EmptyStateView(
                        title: "Trend unavailable",
                        caption: "Forecast endpoint didn't return data for this region.",
                        systemImage: "waveform.path"
                    )
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .task { await load() }
    }

    private var caption: String {
        guard let trend else { return regionName }
        switch trend.trendDirection {
        case .rising: return "▲ Rising — verified pipeline"
        case .falling: return "▼ Falling — verified pipeline"
        case .stable: return "→ Stable — verified pipeline"
        }
    }

    @ViewBuilder
    private func expectedRow(_ trend: RegionTrend) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: Theme.Spacing.lg) {
            VStack(alignment: .leading, spacing: 2) {
                Text("EXPECTED · \(trend.horizonDays)D")
                    .font(Theme.Font.monoCaption).tracking(0.6)
                    .foregroundStyle(Theme.Color.textMuted)
                Text(String(format: "%.1f", trend.next30dExpected))
                    .font(Theme.Font.titleLarge)
                    .foregroundStyle(Theme.Color.textPrimary)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text("80% BAND")
                    .font(Theme.Font.monoCaption).tracking(0.6)
                    .foregroundStyle(Theme.Color.textMuted)
                Text(String(format: "%.1f – %.1f", trend.next30dLo, trend.next30dHi))
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
            Spacer()
        }
    }

    private func load() async {
        loading = true
        let result = await api.fetchTrend(geoid: geoid)
        await MainActor.run {
            self.trend = result
            self.failed = result == nil
            self.loading = false
        }
    }
}

private struct TrendChartContent: View {
    let trend: RegionTrend

    private struct Row: Identifiable {
        let id: String
        let date: String
        let value: Double
        let lo: Double
        let hi: Double
        let isForecast: Bool
    }

    private var rows: [Row] {
        var out: [Row] = []
        for (i, p) in trend.history.enumerated() {
            out.append(Row(id: "h-\(i)", date: p.date, value: p.value, lo: p.value, hi: p.value, isForecast: false))
        }
        for (i, p) in trend.forecast.enumerated() {
            out.append(Row(id: "f-\(i)", date: p.date, value: p.value, lo: p.lo, hi: p.hi, isForecast: true))
        }
        return out
    }

    var body: some View {
        Chart(rows) { row in
            if row.isForecast {
                AreaMark(
                    x: .value("Date", row.date),
                    yStart: .value("Lo", row.lo),
                    yEnd: .value("Hi", row.hi)
                )
                .foregroundStyle(Theme.Color.accent.opacity(0.18))
                LineMark(
                    x: .value("Date", row.date),
                    y: .value("Value", row.value)
                )
                .lineStyle(StrokeStyle(lineWidth: 1.6, dash: [4, 3]))
                .foregroundStyle(Theme.Color.accent)
            } else {
                LineMark(
                    x: .value("Date", row.date),
                    y: .value("Value", row.value)
                )
                .lineStyle(StrokeStyle(lineWidth: 1.6))
                .foregroundStyle(Theme.Color.accent)
            }
        }
        .chartXAxis {
            AxisMarks(values: .automatic(desiredCount: 4)) { _ in
                AxisGridLine().foregroundStyle(Theme.Color.border)
                AxisValueLabel().foregroundStyle(Theme.Color.textMuted)
            }
        }
        .chartYAxis {
            AxisMarks { _ in
                AxisGridLine().foregroundStyle(Theme.Color.border)
                AxisValueLabel().foregroundStyle(Theme.Color.textMuted)
            }
        }
    }
}

// MARK: - Crime pattern breakdown card

struct RegionBreakdownCard: View {
    let geoid: String
    @Environment(APIClient.self) private var api

    @State private var breakdown: RegionBreakdown?
    @State private var loading = true

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(
                    title: "Crime pattern breakdown",
                    caption: breakdown.map { "Next \($0.windowDays)d · ≈\($0.total30d) incidents" } ?? "Next 30 days"
                )

                if loading {
                    LoadingView(label: "Loading breakdown…").frame(height: 120)
                } else if let breakdown, !breakdown.categories.isEmpty {
                    VStack(spacing: 8) {
                        ForEach(breakdown.categories) { row in
                            categoryRow(row, max: breakdown.categories.map(\.count30d).max() ?? 1)
                        }
                    }
                    Text(breakdown.note)
                        .font(Theme.Font.monoCaption)
                        .tracking(0.4)
                        .foregroundStyle(Theme.Color.textMuted)
                } else {
                    EmptyStateView(
                        title: "No breakdown",
                        caption: "Category breakdown isn't available for this region.",
                        systemImage: "chart.bar"
                    )
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .task { await load() }
    }

    private func categoryRow(_ row: BreakdownCategory, max: Int) -> some View {
        let frac = max > 0 ? Double(row.count30d) / Double(max) : 0
        let trendColor: Color = row.trendDirection == .rising
            ? Theme.Color.high
            : row.trendDirection == .falling ? Theme.Color.low : Theme.Color.textSecondary
        let glyph = row.trendDirection == .rising ? "▲" : row.trendDirection == .falling ? "▼" : "→"
        return VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(row.label)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)
                Spacer()
                Text("\(row.count30d)")
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.textPrimary)
                Text("\(glyph) \(row.trendPct >= 0 ? "+" : "")\(String(format: "%.1f", row.trendPct))%")
                    .font(Theme.Font.mono)
                    .foregroundStyle(trendColor)
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2).fill(Theme.Color.border).frame(height: 4)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(trendColor.opacity(0.85))
                        .frame(width: geo.size.width * CGFloat(frac), height: 4)
                }
            }
            .frame(height: 4)
        }
    }

    private func load() async {
        loading = true
        let result = await api.fetchBreakdown(geoid: geoid)
        await MainActor.run {
            self.breakdown = result
            self.loading = false
        }
    }
}

// MARK: - Pricing guidance card

struct RegionPricingCard: View {
    let geoid: String
    @Environment(APIClient.self) private var api

    @State private var persona: PricingPersonaKey = .insurer
    @State private var basePremium: Double = PricingPersonaKey.insurer.defaultBase
    @State private var quote: PricingQuote?
    @State private var loading = true
    @State private var loadToken = UUID()

    var body: some View {
        Card(background: Theme.Color.accent.opacity(0.06)) {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                SectionHeader(title: "Pricing guidance", caption: "Auditable suggestion")

                personaToggle

                baseInput

                if loading {
                    LoadingView(label: "Calculating…").frame(height: 100)
                } else if let quote {
                    headline(quote)
                    metaRow(quote)
                    drivers(quote)
                    if !quote.caveats.isEmpty {
                        caveats(quote)
                    }
                    methodology(quote)
                } else {
                    EmptyStateView(
                        title: "Pricing unavailable",
                        caption: "Quote endpoint didn't return data for this region.",
                        systemImage: "dollarsign.circle"
                    )
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .task(id: loadToken) { await load() }
    }

    private var personaToggle: some View {
        HStack(spacing: 6) {
            ForEach(PricingPersonaKey.allCases) { p in
                Button {
                    persona = p
                    basePremium = p.defaultBase
                    loadToken = UUID()
                } label: {
                    Text(p.displayName.uppercased())
                        .font(Theme.Font.monoCaption)
                        .tracking(0.6)
                        .padding(.vertical, 4)
                        .padding(.horizontal, 8)
                        .background(persona == p ? Theme.Color.accent : Theme.Color.bgRaised, in: RoundedRectangle(cornerRadius: 4))
                        .foregroundStyle(persona == p ? Theme.Color.bg : Theme.Color.textSecondary)
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
    }

    private var baseInput: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(persona.baseLabel.uppercased())
                .font(Theme.Font.monoCaption)
                .tracking(0.6)
                .foregroundStyle(Theme.Color.textMuted)
            HStack {
                Text("$")
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.textSecondary)
                TextField("Base", value: $basePremium, formatter: Self.currencyFormatter)
                    .keyboardType(.decimalPad)
                    .font(Theme.Font.title)
                    .foregroundStyle(Theme.Color.textPrimary)
                    .submitLabel(.done)
                    .onSubmit { loadToken = UUID() }
                Spacer()
                Button("Update") { loadToken = UUID() }
                    .font(Theme.Font.monoCaption)
                    .tracking(0.6)
                    .foregroundStyle(Theme.Color.accent)
            }
            .padding(8)
            .background(Theme.Color.bgRaised, in: RoundedRectangle(cornerRadius: 6))
        }
    }

    private static let currencyFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        f.maximumFractionDigits = 2
        return f
    }()

    private func headline(_ q: PricingQuote) -> some View {
        let bandColor: Color = {
            switch q.band {
            case .preferred: return Theme.Color.low
            case .standard: return Theme.Color.textPrimary
            case .surcharge: return Theme.Color.elevated
            case .high_risk, .decline_recommended: return Theme.Color.high
            }
        }()
        let deltaPct = (q.riskMultiplier - 1) * 100
        return HStack(alignment: .lastTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text("SUGGESTED")
                    .font(Theme.Font.monoCaption).tracking(0.6)
                    .foregroundStyle(Theme.Color.textMuted)
                Text("$\(String(format: "%.2f", q.suggestedPremium))")
                    .font(Theme.Font.titleLarge)
                    .foregroundStyle(bandColor)
                Text("\(String(format: "%.2f", q.riskMultiplier))× base · \(deltaPct >= 0 ? "+" : "")\(String(format: "%.1f", deltaPct))%")
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
            Spacer()
            Text(q.band.displayName.uppercased())
                .font(Theme.Font.monoCaption).tracking(0.7)
                .padding(.vertical, 4)
                .padding(.horizontal, 8)
                .background(bandColor.opacity(0.15), in: RoundedRectangle(cornerRadius: 4))
                .foregroundStyle(bandColor)
        }
    }

    private func metaRow(_ q: PricingQuote) -> some View {
        HStack(spacing: 12) {
            metaCell("CONF", String(format: "%.0f%%", q.confidence * 100))
            metaCell("α", String(format: "%.2f", q.alpha))
            metaCell("β", String(format: "%.2f", q.beta))
            metaCell("RISK Δ", String(format: "%+.0f%%", q.riskFactor * 100))
            Spacer()
        }
    }

    private func metaCell(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(Theme.Font.monoCaption).tracking(0.6)
                .foregroundStyle(Theme.Color.textMuted)
            Text(value)
                .font(Theme.Font.mono)
                .foregroundStyle(Theme.Color.textPrimary)
        }
    }

    private func drivers(_ q: PricingQuote) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("WHY THIS PRICE")
                .font(Theme.Font.monoCaption).tracking(0.7)
                .foregroundStyle(Theme.Color.textMuted)
            ForEach(q.drivers) { d in
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(d.name)
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textPrimary)
                        Text(d.evidence)
                            .font(Theme.Font.label)
                            .foregroundStyle(Theme.Color.textSecondary)
                    }
                    Spacer()
                    Text("\(d.contributionPct >= 0 ? "+" : "")\(String(format: "%.1f", d.contributionPct))%")
                        .font(Theme.Font.mono)
                        .foregroundStyle(d.contributionPct > 0 ? Theme.Color.high : d.contributionPct < 0 ? Theme.Color.low : Theme.Color.textSecondary)
                }
            }
        }
    }

    private func caveats(_ q: PricingQuote) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(q.caveats, id: \.self) { c in
                HStack(alignment: .top, spacing: 6) {
                    Text("•").foregroundStyle(Theme.Color.elevated)
                    Text(c).font(Theme.Font.label).foregroundStyle(Theme.Color.textSecondary)
                }
            }
        }
    }

    private func methodology(_ q: PricingQuote) -> some View {
        Text(q.methodology)
            .font(Theme.Font.monoCaption)
            .tracking(0.4)
            .foregroundStyle(Theme.Color.textMuted)
    }

    private func load() async {
        loading = true
        let result = await api.fetchPricing(geoid: geoid, persona: persona, basePremium: basePremium)
        await MainActor.run {
            self.quote = result
            self.loading = false
        }
    }
}
