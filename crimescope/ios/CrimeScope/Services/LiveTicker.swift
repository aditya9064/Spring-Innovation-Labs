import Foundation
import Observation

@Observable
final class LiveTicker {
    private(set) var newEventIds: Set<String> = []
    private var timer: Timer?
    var onNewEvent: ((LiveEvent) -> Void)?

    func start(geoid: String? = nil) {
        stop()
        timer = Timer.scheduledTimer(withTimeInterval: 35, repeats: true) { [weak self] _ in
            guard let self else { return }
            let event = MockData.liveEvents(for: geoid, limit: 1).first
            guard let event else { return }
            self.newEventIds.insert(event.id)
            self.onNewEvent?(event)
            DispatchQueue.main.asyncAfter(deadline: .now() + 6) { [weak self] in
                self?.newEventIds.remove(event.id)
            }
        }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    deinit { stop() }
}

enum BlindSpots {
    struct Entry: Identifiable, Hashable {
        let id: String
        let name: String
        let underreportingRisk: Double
        let coverageScore: Double
        let reason: String
    }

    /// Compute blind-spot entries from a list of currently-loaded `TractScore`s.
    /// We approximate the trust-passport metrics from the score row's own
    /// confidence and ML-vs-baseline divergence instead of synthesising from
    /// `MockData`. Callers can pass either live or mock tract data.
    static func compute(from tracts: [TractScore]) -> [Entry] {
        guard !tracts.isEmpty else { return [] }
        return tracts
            .map { tract -> Entry in
                let divergence = abs(tract.mlScore - tract.baselineScore) / max(1, tract.baselineScore)
                // Underreporting proxy: low confidence + low scored severity
                let underreporting = max(0, min(1, (1 - tract.confidence) * (1 + divergence * 0.5)))
                let coverage = tract.confidence
                let reason: String
                if underreporting > 0.4 {
                    reason = "Low model confidence and notable ML/baseline divergence — reported score may be conservative."
                } else if coverage < 0.7 {
                    reason = "Coverage gaps in supplemental sources for this region; verify before confident decisions."
                } else {
                    reason = "Mild signal mismatch; treat with caution at the margin."
                }
                return Entry(
                    id: tract.geoid,
                    name: tract.name,
                    underreportingRisk: underreporting,
                    coverageScore: coverage,
                    reason: reason
                )
            }
            .filter { $0.underreportingRisk > 0.18 || $0.coverageScore < 0.78 }
            .sorted { $0.underreportingRisk > $1.underreportingRisk }
    }

    /// Backwards-compat shim — defaults to `MockData.tracts` when the caller
    /// can't or won't pass live data. Prefer the `from:` overload.
    static func compute() -> [Entry] {
        compute(from: MockData.tracts)
    }
}
