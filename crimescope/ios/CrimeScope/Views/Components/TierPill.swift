import SwiftUI

struct TierPill: View {
    let tier: RiskTier
    var size: Size = .md
    var withScore: Double? = nil

    enum Size { case sm, md, lg }

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(tier.color)
                .frame(width: dotSize, height: dotSize)
            Text(tier.rawValue.uppercased())
                .font(labelFont)
                .foregroundStyle(tier.color)
                .tracking(0.6)
            if let score = withScore {
                Text("·")
                    .foregroundStyle(Theme.Color.textMuted)
                Text(Format.score(score))
                    .font(scoreFont)
                    .foregroundStyle(tier.color)
            }
        }
        .padding(.horizontal, hPad)
        .padding(.vertical, vPad)
        .background(tier.fillColor, in: RoundedRectangle(cornerRadius: Theme.Radius.pill))
        .overlay {
            RoundedRectangle(cornerRadius: Theme.Radius.pill)
                .stroke(tier.color.opacity(0.35), lineWidth: 0.5)
        }
    }

    private var dotSize: CGFloat {
        switch size { case .sm: return 5; case .md: return 6; case .lg: return 8 }
    }
    private var labelFont: Font {
        switch size { case .sm: return Theme.Font.monoCaption; case .md: return Theme.Font.mono; case .lg: return Theme.Font.title }
    }
    private var scoreFont: Font {
        switch size { case .sm: return Theme.Font.monoCaption; case .md: return Theme.Font.mono; case .lg: return Theme.Font.monoNumber }
    }
    private var hPad: CGFloat {
        switch size { case .sm: return 8; case .md: return 10; case .lg: return 14 }
    }
    private var vPad: CGFloat {
        switch size { case .sm: return 3; case .md: return 4; case .lg: return 6 }
    }
}

#Preview {
    VStack {
        TierPill(tier: .critical)
        TierPill(tier: .high, size: .lg, withScore: 72.4)
        TierPill(tier: .moderate, size: .sm)
    }
    .padding()
    .background(Theme.Color.bg)
}
