import Foundation
import Observation

@Observable
final class AuditStore {
    private(set) var entries: [AuditRecord] = []
    private let defaults = UserDefaults.standard
    private let key = "cs.audit.entries"

    init() { load() }

    func load() {
        guard let data = defaults.data(forKey: key),
              let decoded = try? JSONDecoder.iso.decode([AuditRecord].self, from: data) else {
            entries = AuditStore.seed
            persist()
            return
        }
        entries = decoded.sorted { $0.createdAt > $1.createdAt }
    }

    func add(_ record: AuditRecord) {
        entries.insert(record, at: 0)
        persist()
    }

    private func persist() {
        if let data = try? JSONEncoder.iso.encode(entries) {
            defaults.set(data, forKey: key)
        }
    }

    private static let seed: [AuditRecord] = {
        let names = ["Logan Square", "Englewood", "Lincoln Park"]
        let geoids = ["17031010001", "17031020002", "17031030003"]
        return zip(names, geoids).enumerated().map { idx, pair in
            AuditRecord(
                id: UUID().uuidString,
                geoid: pair.1,
                regionName: pair.0,
                persona: idx == 0 ? .insurance : (idx == 1 ? .publicSafety : .real_estate),
                riskScore: [62.0, 81.0, 38.0][idx],
                riskTier: [.elevated, .critical, .moderate][idx],
                decision: ["Approved with surcharge", "Manual review", "Auto-approve"][idx],
                rationale: [
                    "Live signals diverge upward but underreporting risk is moderate; documented for audit.",
                    "Verified baseline + live signals both critical. Escalated to senior analyst.",
                    "Score and trust posture both stable; standard tier applied."
                ][idx],
                overrodeMl: idx == 1,
                createdAt: Date().addingTimeInterval(-Double((idx + 1) * 3600 * 6))
            )
        }
    }()
}

@Observable
final class ChallengeStore {
    private(set) var entries: [ChallengeRecord] = []
    private let defaults = UserDefaults.standard
    private let key = "cs.challenge.entries"

    init() { load() }

    func load() {
        guard let data = defaults.data(forKey: key),
              let decoded = try? JSONDecoder.iso.decode([ChallengeRecord].self, from: data) else {
            entries = ChallengeStore.seed
            persist()
            return
        }
        entries = decoded.sorted { $0.createdAt > $1.createdAt }
    }

    func add(_ record: ChallengeRecord) {
        entries.insert(record, at: 0)
        persist()
    }

    private func persist() {
        if let data = try? JSONEncoder.iso.encode(entries) {
            defaults.set(data, forKey: key)
        }
    }

    private static let seed: [ChallengeRecord] = [
        ChallengeRecord(
            id: UUID().uuidString,
            geoid: "17031020002",
            regionName: "Englewood",
            challengerName: "Aisha Roberts",
            challengeType: .data,
            evidence: "Block-level CPD logs show 3 reclassifications in last 14d; underreporting risk understated.",
            proposedAdjustment: -4.5,
            status: .in_review,
            createdAt: Date().addingTimeInterval(-86400 * 2)
        ),
        ChallengeRecord(
            id: UUID().uuidString,
            geoid: "17031010001",
            regionName: "Logan Square",
            challengerName: "Marc Chen",
            challengeType: .model,
            evidence: "ML adjustment overweights social signals during weekend windows; suggest dampening factor.",
            proposedAdjustment: -2.0,
            status: .pending,
            createdAt: Date().addingTimeInterval(-3600 * 18)
        )
    ]
}

extension JSONEncoder {
    static var iso: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}

extension JSONDecoder {
    static var iso: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { dec in
            let container = try dec.singleValueContainer()
            let raw = try container.decode(String.self)
            if let d = ISO8601DateFormatter.fractional.date(from: raw) { return d }
            if let d = ISO8601DateFormatter.plain.date(from: raw) { return d }
            for f in DateFormatter.backendCandidates {
                if let d = f.date(from: raw) { return d }
            }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unrecognized date: \(raw)")
        }
        return decoder
    }
}
