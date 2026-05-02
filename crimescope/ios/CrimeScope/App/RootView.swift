import SwiftUI

struct RootView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        Group {
            if store.hasOnboarded {
                MainTabs()
            } else {
                OnboardingView()
            }
        }
        .background(Theme.Color.bg)
    }
}

struct MainTabs: View {
    @State private var selection: Tab = .map

    enum Tab: Hashable { case map, compare }

    var body: some View {
        // Two tabs only — directly answering the problem statement's two
        // primary verbs: "score one area" (Map → Region) and "compare two
        // areas" (Compare). Auxiliary surfaces (live, reports, audit,
        // challenge, blind spots, settings) are reachable from the gear
        // menu in the Map top bar so they don't dilute the main flow.
        TabView(selection: $selection) {
            MapTabContainer()
                .tabItem {
                    Label("Map", systemImage: "map.fill")
                }
                .tag(Tab.map)

            ComparePickerView()
                .tabItem {
                    Label("Compare", systemImage: "rectangle.split.2x1")
                }
                .tag(Tab.compare)
        }
        .tint(Theme.Color.accent)
    }
}
