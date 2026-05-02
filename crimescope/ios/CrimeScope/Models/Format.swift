import Foundation

enum Format {
    static func score(_ value: Double) -> String {
        String(format: "%.1f", value)
    }

    static func scoreInt(_ value: Double) -> String {
        String(Int(value.rounded()))
    }

    static func percent(_ value: Double, fractionDigits: Int = 0) -> String {
        let pct = value * 100
        return String(format: "%.\(fractionDigits)f%%", pct)
    }

    static func delta(_ value: Double) -> String {
        let sign = value > 0 ? "+" : ""
        return "\(sign)\(String(format: "%.1f", value))"
    }

    static func deltaShort(_ value: Double) -> String {
        let sign = value > 0 ? "+" : value < 0 ? "" : "±"
        return "\(sign)\(String(format: "%.1f", value))"
    }

    static func tierFromScore(_ score: Double) -> RiskTier {
        switch score {
        case 80...: return .critical
        case 65..<80: return .high
        case 50..<65: return .elevated
        case 35..<50: return .moderate
        default: return .low
        }
    }

    static func shortGeoid(_ geoid: String) -> String {
        guard geoid.count > 6 else { return geoid }
        let suffix = geoid.suffix(6)
        return "…\(suffix)"
    }

    static func timeAgo(_ date: Date, now: Date = Date()) -> String {
        let seconds = now.timeIntervalSince(date)
        if seconds < 60 { return "\(Int(seconds))s ago" }
        if seconds < 3600 { return "\(Int(seconds / 60))m ago" }
        if seconds < 86400 { return "\(Int(seconds / 3600))h ago" }
        let days = Int(seconds / 86400)
        if days < 30 { return "\(days)d ago" }
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        return formatter.string(from: date)
    }

    static func dateTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, h:mm a"
        return formatter.string(from: date)
    }

    static func impactToBars(_ impact: Double) -> String {
        let normalized = max(0, min(1, abs(impact)))
        let count = Int(normalized * 5)
        let filled = String(repeating: "▮", count: count)
        let empty = String(repeating: "▯", count: 5 - count)
        return filled + empty
    }

    static func directionGlyph(_ direction: Driver.Direction) -> String {
        switch direction {
        case .up: return "▲"
        case .down: return "▼"
        case .neutral: return "◆"
        }
    }
}
