import Foundation
import Observation

@Observable
final class AppStore {
    var hasOnboarded: Bool {
        didSet { defaults.set(hasOnboarded, forKey: Keys.hasOnboarded) }
    }
    var city: String {
        didSet { defaults.set(city, forKey: Keys.city) }
    }
    var persona: Persona {
        didSet { defaults.set(persona.rawValue, forKey: Keys.persona) }
    }
    var apiBaseURL: String {
        didSet { defaults.set(apiBaseURL, forKey: Keys.apiBaseURL) }
    }
    var watchlist: Set<String> {
        didSet {
            defaults.set(Array(watchlist), forKey: Keys.watchlist)
        }
    }

    var usingMocks: Bool = true
    var probeAttempted: Bool = false

    var selectedTract: TractScore? = nil
    var tierFilter: Set<RiskTier> = Set(RiskTier.allCases)
    var chatOpen: Bool = false

    private let defaults: UserDefaults

    enum Keys {
        static let hasOnboarded = "cs.hasOnboarded"
        static let city = "cs.city"
        static let persona = "cs.persona"
        static let apiBaseURL = "cs.apiBaseURL"
        static let watchlist = "cs.watchlist"
        static let migrationVersion = "cs.migrationVersion"
    }

    static let defaultCity = "uk"
    static let supportedCities: Set<String> = ["uk", "uk_lsoa", "chicago"]
    static let currentMigration = 2

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.hasOnboarded = defaults.bool(forKey: Keys.hasOnboarded)

        let storedCity = defaults.string(forKey: Keys.city)
        let migration = defaults.integer(forKey: Keys.migrationVersion)

        // Migration v2: backend defaults to UK (England & Wales). Older builds
        // defaulted iOS to "chicago" and offered fake US-only city options.
        // Force any unsupported or pre-migration city back to the UK default,
        // and re-trigger onboarding so the user picks a real backend city.
        if migration < AppStore.currentMigration {
            let needsCityFix = storedCity == nil
                || !AppStore.supportedCities.contains(storedCity ?? "")
            if needsCityFix {
                self.city = AppStore.defaultCity
                defaults.set(AppStore.defaultCity, forKey: Keys.city)
                self.hasOnboarded = false
                defaults.set(false, forKey: Keys.hasOnboarded)
            } else {
                self.city = storedCity ?? AppStore.defaultCity
            }
            defaults.set(AppStore.currentMigration, forKey: Keys.migrationVersion)
        } else {
            self.city = storedCity ?? AppStore.defaultCity
        }

        let personaRaw = defaults.string(forKey: Keys.persona) ?? Persona.insurance.rawValue
        self.persona = Persona(rawValue: personaRaw) ?? .insurance
        self.apiBaseURL = defaults.string(forKey: Keys.apiBaseURL) ?? "http://10.100.192.233:8000"
        let watchArray = defaults.stringArray(forKey: Keys.watchlist) ?? []
        self.watchlist = Set(watchArray)
    }

    func toggleWatchlist(_ geoid: String) {
        if watchlist.contains(geoid) {
            watchlist.remove(geoid)
        } else {
            watchlist.insert(geoid)
        }
    }

    func resetOnboarding() {
        hasOnboarded = false
    }
}
