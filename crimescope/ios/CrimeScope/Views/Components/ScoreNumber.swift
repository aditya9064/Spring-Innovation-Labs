import SwiftUI

struct ScoreNumber: View {
    let value: Double
    var label: String? = nil
    var size: Size = .lg
    var tint: Color? = nil

    enum Size { case sm, md, lg, xl }

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            if let label {
                Text(label.uppercased())
                    .font(Theme.Font.monoCaption)
                    .foregroundStyle(Theme.Color.textMuted)
                    .tracking(0.7)
            }
            Text(Format.score(value))
                .font(numberFont)
                .foregroundStyle(tint ?? Theme.Color.textPrimary)
                .monospacedDigit()
        }
    }

    private var numberFont: Font {
        switch size {
        case .sm: return Theme.Font.mono
        case .md: return Theme.Font.monoNumber
        case .lg: return Theme.Font.monoNumberLarge
        case .xl: return .system(size: 56, weight: .semibold, design: .monospaced)
        }
    }
}

struct DeltaPill: View {
    let delta: Double
    var label: String = "Δ"

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(Theme.Font.monoCaption)
                .foregroundStyle(Theme.Color.textMuted)
            Text(Format.delta(delta))
                .font(Theme.Font.mono)
                .foregroundStyle(color)
                .monospacedDigit()
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: Theme.Radius.pill))
    }

    private var color: Color {
        if delta > 1 { return Theme.Color.high }
        if delta < -1 { return Theme.Color.low }
        return Theme.Color.textSecondary
    }
}
