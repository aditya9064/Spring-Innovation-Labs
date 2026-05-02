import SwiftUI

@main
struct CrimeScopeApp: App {
    @State private var store: AppStore
    @State private var apiClient: APIClient
    @State private var auditStore = AuditStore()
    @State private var challengeStore = ChallengeStore()

    init() {
        let store = AppStore()
        _store = State(initialValue: store)
        _apiClient = State(initialValue: APIClient(store: store))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(apiClient)
                .environment(auditStore)
                .environment(challengeStore)
                .preferredColorScheme(.dark)
                .task { await apiClient.probeOnLaunch() }
        }
    }
}
