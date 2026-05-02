import SwiftUI

/// The plain-language summary line that anchors the Region sheet.
///
/// Directly answers the "without requiring users to be crime/data experts"
/// promise from the problem statement: one paragraph, no jargon, that names
/// the score, the biggest reason, the trend, and the implication for the
/// user's persona.
struct RegionSummaryLine: View {
    let tract: TractScore
    let pkg: TractRiskPackage
    let persona: Persona

    var body: some View {
        Card(background: Theme.Color.bgPanel) {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                Text("WHAT THIS MEANS")
                    .font(Theme.Font.monoCaption)
                    .tracking(0.7)
                    .foregroundStyle(Theme.Color.textMuted)

                Text(summary)
                    .font(Theme.Font.titleLarge)
                    .foregroundStyle(Theme.Color.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)
                    .lineSpacing(2)
            }
        }
    }

    // MARK: - Sentence assembly

    private var summary: String {
        let tier = Format.tierFromScore(pkg.scores.overall)
        let scoreText = "\(pkg.name) scores \(Int(pkg.scores.overall.rounded())) of 100 — \(tier.label)."
        return [scoreText, driverSentence, trendSentence, personaSentence]
            .compactMap { $0 }
            .joined(separator: " ")
    }

    private var driverSentence: String? {
        guard let top = pkg.drivers.first else { return nil }
        let verb = top.direction == .up ? "raising" : top.direction == .down ? "lowering" : "shaping"
        return "The biggest factor is \(top.label.lowercased()), \(verb) the score."
    }

    private var trendSentence: String? {
        switch tract.trendDirection {
        case .rising:
            return "Risk is trending up over the next month — expect about \(predictedText) reported incidents."
        case .falling:
            return "Risk is trending down over the next month — expect about \(predictedText) reported incidents."
        case .stable:
            return "Risk is holding steady over the next month — expect about \(predictedText) reported incidents."
        case .none:
            return nil
        }
    }

    private var predictedText: String {
        guard tract.predictedNext30d > 0 else { return "the citywide average" }
        return "\(Int(tract.predictedNext30d.rounded()))"
    }

    private var personaSentence: String? {
        let tier = Format.tierFromScore(pkg.scores.overall)
        switch persona {
        case .insurance:
            switch tier {
            case .low:        return "For underwriting, this fits a preferred premium with no surcharge."
            case .moderate:   return "For underwriting, this is standard — minor risk loading."
            case .elevated:   return "For underwriting, expect a moderate premium surcharge."
            case .high:       return "For underwriting, expect a substantial surcharge or extra review."
            case .critical:   return "For underwriting, manual review and a high surcharge are recommended."
            }
        case .real_estate:
            switch tier {
            case .low:        return "For property pricing, this is a low-risk neighbourhood — minimal adjustment."
            case .moderate:   return "For property pricing, this is around the regional average."
            case .elevated:   return "For property pricing, expect a discount of a few percent."
            case .high:       return "For property pricing, a noticeable discount is warranted."
            case .critical:   return "For property pricing, deep diligence is recommended before any deal."
            }
        case .publicSafety:
            switch tier {
            case .low, .moderate:   return "For deployment, this area does not require additional resourcing right now."
            case .elevated:         return "For deployment, consider routine patrol density review."
            case .high, .critical:  return "For deployment, this area warrants a tactical review and added presence."
            }
        case .logistics:
            switch tier {
            case .low, .moderate:   return "For routing, no special precautions needed for normal hours."
            case .elevated:         return "For routing, prefer daylight windows and avoid extended dwell time."
            case .high, .critical:  return "For routing, restrict to daylight hours or reroute through adjacent areas."
            }
        case .civic:
            return "For community planning, see the breakdown below for the dominant offence categories."
        case .journalist:
            return "For reporting, the trust panel below covers source agreement and underreporting risk."
        }
    }
}

private extension RiskTier {
    var label: String {
        switch self {
        case .low:        return "Low risk"
        case .moderate:   return "Moderate risk"
        case .elevated:   return "Elevated risk"
        case .high:       return "High risk"
        case .critical:   return "Critical risk"
        }
    }
}
