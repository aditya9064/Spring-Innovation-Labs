import SwiftUI
import CoreLocation

struct MapTabContainer: View {
    @Environment(AppStore.self) private var store
    @Environment(APIClient.self) private var api

    @State private var tracts: [TractScore] = []
    @State private var polygons: [TractPolygon] = []
    @State private var loading: Bool = true
    @State private var selectedTract: TractScore?
    @State private var searchPresented: Bool = false
    @State private var settingsPresented: Bool = false
    @State private var mapMode: MapMode = .threeD
    @State private var location = LocationManager()
    @State private var recenterNonce: Int = 0
    @State private var searchHit: TractScore?
    @State private var searchNonce: Int = 0

    var body: some View {
        @Bindable var bindable = store
        ZStack(alignment: .top) {
            Theme.Color.bg.ignoresSafeArea()

            if loading {
                LoadingView(label: "Loading regions…")
            } else {
                RegionMapView(
                    polygons: polygons,
                    allowedTiers: bindable.tierFilter,
                    selectedGeoid: selectedTract?.geoid,
                    selectedCoordinate: selectedTract?.centroid.clLocation,
                    userCoordinate: location.lastLocation?.coordinate,
                    recenterNonce: recenterNonce,
                    mode: mapMode,
                    defaultCenter: MockData.defaultCenter(forCity: store.city),
                    defaultAltitude2D: MockData.defaultAltitude(forCity: store.city),
                    searchHighlightGeoid: searchHit?.geoid,
                    searchHighlightCoordinate: searchHit?.centroid.clLocation,
                    searchNonce: searchNonce,
                    onSelect: { geoid in
                        if let t = tracts.first(where: { $0.geoid == geoid }) {
                            selectedTract = t
                            // Tapping a different tract clears the search highlight,
                            // matching the web's clearSearchHighlight on overview/clear.
                            if t.geoid != searchHit?.geoid {
                                searchHit = nil
                            }
                        }
                    }
                )
                .ignoresSafeArea(edges: [.bottom])
            }

            VStack(spacing: Theme.Spacing.sm) {
                topBar
                    .padding(.horizontal, Theme.Spacing.lg)
                KpiStrip(tracts: tracts.filter { bindable.tierFilter.contains($0.tier) })
                    .padding(.horizontal, Theme.Spacing.lg)
                TierFilterBar(allowed: $bindable.tierFilter)
                    .padding(.leading, Theme.Spacing.lg)
            }
            .padding(.top, Theme.Spacing.sm)

            VStack {
                Spacer()
                MapLegend()
                    .padding(.horizontal, Theme.Spacing.lg)
                    .padding(.bottom, Theme.Spacing.lg)
            }
            .allowsHitTesting(false)
        }
        .task {
            location.requestWhenInUse()
            await load()
        }
        .onChange(of: store.city) { _, _ in
            selectedTract = nil
            searchHit = nil
            tracts = []
            polygons = []
            Task { await load() }
        }
        .sheet(item: $selectedTract) { tract in
            RegionSheet(tract: tract)
                .presentationDetents([.fraction(0.45), .fraction(0.85)])
                .presentationDragIndicator(.visible)
                .presentationBackground(Theme.Color.bg)
        }
        .sheet(isPresented: $searchPresented) {
            TractSearchSheet(tracts: tracts) { tract in
                searchPresented = false
                searchHit = tract
                searchNonce &+= 1
                selectedTract = tract
            }
            .presentationDetents([.large])
            .presentationBackground(Theme.Color.bg)
        }
        .sheet(isPresented: $settingsPresented) {
            NavigationStack {
                SettingsView()
            }
            .presentationDetents([.large])
            .presentationBackground(Theme.Color.bg)
        }
    }

    private var topBar: some View {
        HStack(spacing: Theme.Spacing.sm) {
            HStack(spacing: 6) {
                Text("CRIMESCOPE")
                    .font(Theme.Font.monoCaption)
                    .tracking(1.4)
                    .foregroundStyle(Theme.Color.textSecondary)
                Text("/ \(store.city.uppercased())")
                    .font(Theme.Font.monoCaption)
                    .tracking(1.4)
                    .foregroundStyle(Theme.Color.textMuted)
            }
            .padding(.horizontal, 10).padding(.vertical, 6)
            .background(Theme.Color.bgPanel.opacity(0.85), in: Capsule())

            DataSourceBadge(liveLabel: tracts.isEmpty ? "LIVE" : "LIVE · \(tracts.count)")

            Spacer()

            mapModeToggle

            Button {
                location.requestWhenInUse()
                recenterNonce &+= 1
                let g = UIImpactFeedbackGenerator(style: .light)
                g.impactOccurred()
            } label: {
                Image(systemName: "location.fill")
                    .font(.system(size: 14, weight: .semibold))
                    .padding(8)
                    .background(Theme.Color.bgPanel.opacity(0.85), in: Circle())
                    .foregroundStyle(Theme.Color.accent)
            }

            Button {
                searchPresented = true
            } label: {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14, weight: .semibold))
                    .padding(8)
                    .background(Theme.Color.bgPanel.opacity(0.85), in: Circle())
                    .foregroundStyle(Theme.Color.textPrimary)
            }

            Button {
                settingsPresented = true
            } label: {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 14, weight: .semibold))
                    .padding(8)
                    .background(Theme.Color.bgPanel.opacity(0.85), in: Circle())
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
    }

    private var mapModeToggle: some View {
        HStack(spacing: 0) {
            ForEach(MapMode.allCases, id: \.self) { mode in
                Button {
                    withAnimation { mapMode = mode }
                    let g = UISelectionFeedbackGenerator()
                    g.selectionChanged()
                } label: {
                    Text(mode.rawValue)
                        .font(Theme.Font.monoCaption)
                        .tracking(0.8)
                        .foregroundStyle(mapMode == mode ? Theme.Color.bg : Theme.Color.textSecondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(
                            mapMode == mode ? Theme.Color.accent : Color.clear,
                            in: Capsule()
                        )
                }
            }
        }
        .padding(2)
        .background(Theme.Color.bgPanel.opacity(0.85), in: Capsule())
    }

    private func load() async {
        loading = true
        let result = await api.loadCity(store.city)
        await MainActor.run {
            self.tracts = result.scores
            self.polygons = result.polygons
            self.loading = false
        }
    }
}
