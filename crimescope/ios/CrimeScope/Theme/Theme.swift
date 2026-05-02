import SwiftUI

enum Theme {
    enum Color {
        static let bg = SwiftUI.Color(red: 0.039, green: 0.039, blue: 0.039)
        static let bgPanel = SwiftUI.Color(red: 0.067, green: 0.067, blue: 0.067)
        static let bgAlt = SwiftUI.Color(red: 0.086, green: 0.086, blue: 0.086)
        static let bgRaised = SwiftUI.Color(red: 0.12, green: 0.12, blue: 0.12)

        static let textPrimary = SwiftUI.Color.white
        static let textSecondary = SwiftUI.Color(white: 0.65)
        static let textMuted = SwiftUI.Color(white: 0.45)

        static let border = SwiftUI.Color(white: 0.12)
        static let borderStrong = SwiftUI.Color(white: 0.22)

        static let accent = SwiftUI.Color(red: 0.0, green: 0.831, blue: 1.0)
        static let accentMuted = SwiftUI.Color(red: 0.0, green: 0.55, blue: 0.7)

        static let critical = SwiftUI.Color(red: 1.0, green: 0.231, blue: 0.188)
        static let high = SwiftUI.Color(red: 1.0, green: 0.584, blue: 0.0)
        static let elevated = SwiftUI.Color(red: 1.0, green: 0.8, blue: 0.0)
        static let moderate = SwiftUI.Color(red: 0.0, green: 0.831, blue: 1.0)
        static let low = SwiftUI.Color(red: 0.204, green: 0.78, blue: 0.349)
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 32
    }

    enum Radius {
        static let sm: CGFloat = 6
        static let md: CGFloat = 10
        static let lg: CGFloat = 14
        static let xl: CGFloat = 20
        static let pill: CGFloat = 999
    }

    enum Font {
        static let monoCaption = SwiftUI.Font.system(size: 11, weight: .medium, design: .monospaced)
        static let mono = SwiftUI.Font.system(size: 13, weight: .medium, design: .monospaced)
        static let monoNumber = SwiftUI.Font.system(size: 22, weight: .semibold, design: .monospaced)
        static let monoNumberLarge = SwiftUI.Font.system(size: 36, weight: .semibold, design: .monospaced)

        static let caption = SwiftUI.Font.system(size: 11, weight: .medium)
        static let label = SwiftUI.Font.system(size: 13, weight: .medium)
        static let body = SwiftUI.Font.system(size: 15, weight: .regular)
        static let title = SwiftUI.Font.system(size: 17, weight: .semibold)
        static let titleLarge = SwiftUI.Font.system(size: 22, weight: .semibold)
        static let display = SwiftUI.Font.system(size: 28, weight: .bold)
    }
}

extension RiskTier {
    var color: Color {
        switch self {
        case .critical: return Theme.Color.critical
        case .high: return Theme.Color.high
        case .elevated: return Theme.Color.elevated
        case .moderate: return Theme.Color.moderate
        case .low: return Theme.Color.low
        }
    }

    var fillColor: Color {
        color.opacity(0.18)
    }

    var uiColor: UIColor {
        switch self {
        case .critical: return UIColor(red: 1.0, green: 0.231, blue: 0.188, alpha: 1.0)
        case .high: return UIColor(red: 1.0, green: 0.584, blue: 0.0, alpha: 1.0)
        case .elevated: return UIColor(red: 1.0, green: 0.8, blue: 0.0, alpha: 1.0)
        case .moderate: return UIColor(red: 0.0, green: 0.831, blue: 1.0, alpha: 1.0)
        case .low: return UIColor(red: 0.204, green: 0.78, blue: 0.349, alpha: 1.0)
        }
    }
}
