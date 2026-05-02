import Foundation
import Observation

@Observable
final class APIClient {
    private let store: AppStore
    private let session: URLSession
    private var probeTask: Task<Void, Never>?

    private var cachedPolygons: (city: String, value: [TractPolygon])?
    private var centroidCache: [String: Coordinate] = [:]

    init(store: AppStore, session: URLSession = .shared) {
        self.store = store
        self.session = session
        startProbe()
    }

    // MARK: - Probe

    func probeOnLaunch() async {
        await awaitProbe()
    }

    @discardableResult
    func reprobe() async -> Bool {
        startProbe(force: true)
        await awaitProbe()
        return !store.usingMocks
    }

    func awaitProbe() async {
        await probeTask?.value
    }

    private func startProbe(force: Bool = false) {
        if !force, store.probeAttempted { return }
        probeTask = Task { [weak self] in
            await self?.runProbe()
        }
    }

    private func runProbe() async {
        let baseURL = await MainActor.run { store.apiBaseURL }
        guard let url = URL(string: "\(baseURL)/api/health") else {
            await markProbe(reachable: false)
            return
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 4.0
        do {
            let (_, response) = try await session.data(for: request)
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            await markProbe(reachable: ok)
        } catch {
            await markProbe(reachable: false)
        }
    }

    @MainActor
    private func markProbe(reachable: Bool) {
        store.usingMocks = !reachable
        store.probeAttempted = true
    }

    // MARK: - HTTP

    private func get<T: Decodable>(_ path: String, as: T.Type, timeout: TimeInterval = 8.0) async throws -> T {
        let baseURL = await MainActor.run { store.apiBaseURL }
        guard let url = URL(string: "\(baseURL)\(path)") else { throw APIError.badURL }
        var request = URLRequest(url: url)
        request.timeoutInterval = timeout
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.badStatus
        }
        do {
            return try JSONDecoder.iso.decode(T.self, from: data)
        } catch {
            throw APIError.decodeFailed
        }
    }

    private func post<T: Decodable, B: Encodable>(_ path: String, body: B, as: T.Type) async throws -> T {
        let baseURL = await MainActor.run { store.apiBaseURL }
        guard let url = URL(string: "\(baseURL)\(path)") else { throw APIError.badURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.iso.encode(body)
        request.timeoutInterval = 8.0
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.badStatus
        }
        return try JSONDecoder.iso.decode(T.self, from: data)
    }

    // MARK: - City load (scores + polygons together)

    func loadCity(_ city: String) async -> (scores: [TractScore], polygons: [TractPolygon]) {
        await awaitProbe()
        do {
            async let scoresResp: BackendScoresResponse = get(
                "/api/regions/scores?city=\(city)",
                as: BackendScoresResponse.self,
                timeout: 12
            )
            async let geoResp: BackendGeoCollection = get(
                "/api/map/geojson?city=\(city)",
                as: BackendGeoCollection.self,
                timeout: 30
            )
            let (s, g) = try await (scoresResp, geoResp)

            let polygons: [TractPolygon] = g.features.compactMap { BackendMap.tractPolygon(from: $0) }

            var centroids: [String: Coordinate] = [:]
            for poly in polygons {
                centroids[poly.geoid] = BackendMap.centroid(of: poly.coordinates.map { [$0.longitude, $0.latitude] })
            }
            centroidCache = centroids
            cachedPolygons = (city, polygons)

            let scores = s.tracts
                .compactMap { dto in BackendMap.tractScore(from: dto, centroid: dto.tract_geoid.flatMap { centroids[$0] }) }
                .sorted { $0.score > $1.score }

            await MainActor.run { store.usingMocks = false }
            return (scores, polygons)
        } catch {
            await MainActor.run { store.usingMocks = true }
            let mocks = MockData.tracts
            let polys = MockData.polygonsForTracts(mocks)
            return (mocks, polys)
        }
    }

    // MARK: - Risk package

    func fetchRiskPackage(geoid: String) async -> TractRiskPackage? {
        await awaitProbe()
        if !store.usingMocks {
            do {
                let pkg: BackendRiskPackage = try await get(
                    "/api/regions/risk-package?region_id=\(geoid)&city=\(store.city)",
                    as: BackendRiskPackage.self
                )
                let persona = await MainActor.run { store.persona }
                return BackendMap.riskPackage(from: pkg, persona: persona)
            } catch {
                // single-endpoint failure: fall back to mock for THIS call but don't latch global usingMocks
            }
        }
        try? await Task.sleep(for: .milliseconds(160))
        guard let tract = MockData.tracts.first(where: { $0.geoid == geoid }) else { return nil }
        return MockData.riskPackage(for: tract)
    }

    // MARK: - Live events

    func fetchLiveEvents(geoid: String? = nil, limit: Int = 30) async -> [LiveEvent] {
        await awaitProbe()
        if !store.usingMocks {
            let regionParam = geoid.map { "&region_id=\($0)" } ?? ""
            do {
                let events: [BackendLiveEvent] = try await get(
                    "/api/live/feed?city=\(store.city)\(regionParam)",
                    as: [BackendLiveEvent].self
                )
                let mapped = events.prefix(limit).map { BackendMap.liveEvent(from: $0) }
                return Array(mapped)
            } catch {
                // Fall through to mocks for this call
            }
        }
        try? await Task.sleep(for: .milliseconds(140))
        return MockData.liveEvents(for: geoid, limit: limit)
    }

    // MARK: - Compare

    func fetchCompare(left: String, right: String) async -> (CompareSnapshot, CompareSnapshot)? {
        await awaitProbe()
        if !store.usingMocks {
            do {
                let resp: BackendCompareResponse = try await get(
                    "/api/compare?left_region_id=\(left)&right_region_id=\(right)&city=\(store.city)",
                    as: BackendCompareResponse.self
                )
                return (
                    BackendMap.compareSnapshot(from: resp.left),
                    BackendMap.compareSnapshot(from: resp.right)
                )
            } catch {
                // fall through
            }
        }
        try? await Task.sleep(for: .milliseconds(180))
        guard let leftTract = MockData.tracts.first(where: { $0.geoid == left }),
              let rightTract = MockData.tracts.first(where: { $0.geoid == right }) else { return nil }
        return (MockData.compareSnapshot(for: leftTract), MockData.compareSnapshot(for: rightTract))
    }

    // MARK: - Reports

    func fetchReport(geoid: String) async -> ReportSummary? {
        await awaitProbe()
        // Backend reports are text envelopes; for now we synthesize from the live risk package
        // so the report reflects real ML scoring instead of mock data.
        if !store.usingMocks, let pkg = await fetchRiskPackage(geoid: geoid) {
            return ReportSummary(
                geoid: pkg.geoid,
                name: pkg.name,
                tier: Format.tierFromScore(pkg.scores.overall),
                executiveSummary: pkg.trustPassport.summary,
                riskNarrative: pkg.whatChanged.first?.detail ?? pkg.trustPassport.summary,
                trustNotes: "Recommended action: \(pkg.trustPassport.recommendedAction).",
                drivers: pkg.drivers,
                peerCompare: [],
                challenges: [],
                generatedAt: pkg.lastUpdated
            )
        }
        try? await Task.sleep(for: .milliseconds(160))
        guard let tract = MockData.tracts.first(where: { $0.geoid == geoid }) else { return nil }
        return MockData.report(for: tract)
    }

    // MARK: - Trend / forecast

    func fetchTrend(geoid: String, horizonDays: Int = 30, metric: String = "incident_rate") async -> RegionTrend? {
        await awaitProbe()
        if !store.usingMocks {
            do {
                let city = await MainActor.run { store.city }
                return try await get(
                    "/api/regions/trend?region_id=\(geoid)&horizon_days=\(horizonDays)&metric=\(metric)&city=\(city)",
                    as: RegionTrend.self
                )
            } catch {
                // fall through to nil — view shows empty state
            }
        }
        return nil
    }

    // MARK: - Crime pattern breakdown

    func fetchBreakdown(geoid: String) async -> RegionBreakdown? {
        await awaitProbe()
        if !store.usingMocks {
            do {
                let city = await MainActor.run { store.city }
                return try await get(
                    "/api/regions/breakdown?region_id=\(geoid)&city=\(city)",
                    as: RegionBreakdown.self
                )
            } catch {
                // fall through
            }
        }
        return nil
    }

    // MARK: - Pricing guidance

    func fetchPricing(
        geoid: String,
        persona: PricingPersonaKey = .insurer,
        basePremium: Double? = nil
    ) async -> PricingQuote? {
        await awaitProbe()
        if !store.usingMocks {
            do {
                let city = await MainActor.run { store.city }
                var path = "/api/pricing/quote?region_id=\(geoid)&persona=\(persona.rawValue)&city=\(city)"
                if let base = basePremium {
                    path += "&base_premium=\(base)"
                }
                return try await get(path, as: PricingQuote.self)
            } catch {
                // fall through
            }
        }
        return nil
    }

    // MARK: - Interventions / Simulation (currently not exposed by backend)

    func interventions() -> [Intervention] {
        MockData.interventions()
    }

    func simulate(geoid: String, values: [String: Double]) async -> SimulationResult? {
        try? await Task.sleep(for: .milliseconds(160))
        guard let tract = MockData.tracts.first(where: { $0.geoid == geoid }) else { return nil }
        let pkg = MockData.riskPackage(for: tract)
        return MockData.simulate(pkg: pkg, values: values)
    }

    // MARK: - Chat (heuristic, can be wired to /api/chat later)

    func sendChat(message: String, geoid: String?) async -> String {
        try? await Task.sleep(for: .milliseconds(420))
        let regionName = MockData.tracts.first(where: { $0.geoid == geoid })?.name ?? "this region"
        let pkg = geoid.flatMap { id in MockData.tracts.first(where: { $0.geoid == id }).map { MockData.riskPackage(for: $0) } }

        let lower = message.lowercased()
        if lower.contains("why") || lower.contains("driver") {
            let drivers = pkg?.drivers.prefix(2).map(\.label).joined(separator: " · ") ?? "live dispatch volume · verified UCR baseline"
            return "Top contributors in \(regionName): \(drivers). Live signals are advisory; the score-of-record stays anchored to the verified baseline."
        }
        if lower.contains("trust") || lower.contains("confidence") {
            let conf = pkg.map { Format.percent($0.trustPassport.confidence) } ?? "~80%"
            return "Trust posture for \(regionName) is \(conf). \(pkg?.trustPassport.recommendedAction ?? "Use baseline as the score-of-record.")"
        }
        if lower.contains("compare") || lower.contains("vs") {
            return "Open the Compare tab to put \(regionName) next to a peer tract. I can suggest a peer in the same tier if you want — try 'suggest peer'."
        }
        return "I can summarize \(regionName)'s drivers, trust passport, live disagreement, or peer comparison. Try 'why is the score this high' or 'is the live spike trustworthy'."
    }

    func aiSummary(for left: CompareSnapshot, vs right: CompareSnapshot) -> String {
        let dl = abs(left.score - right.score)
        let leader = left.score > right.score ? left.name : right.name
        return "\(leader) carries the higher score by \(Format.score(dl)) points. Trust postures \(abs(left.trust.confidence - right.trust.confidence) < 0.1 ? "are similar" : "differ meaningfully") — weight the recommendation accordingly."
    }

    // MARK: - Compatibility shims (older callers)

    func fetchScores(city: String) async -> [TractScore] {
        await loadCity(city).scores
    }

    func fetchPolygons(city: String) async -> [TractPolygon] {
        if let cached = cachedPolygons, cached.city == city {
            return cached.value
        }
        return await loadCity(city).polygons
    }
}

enum APIError: Error {
    case badURL
    case badStatus
    case decodeFailed
}
