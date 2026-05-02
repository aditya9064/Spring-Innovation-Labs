import SwiftUI
import MapKit
import CoreLocation

struct LookAroundView: View {
    let coordinate: CLLocationCoordinate2D
    let regionName: String
    let tier: RiskTier
    let score: Double
    let polygons: [TractPolygon]
    let selectedGeoid: String

    @Environment(\.dismiss) private var dismiss
    @State private var scene: MKLookAroundScene?
    @State private var loading: Bool = true
    @State private var error: String?
    @State private var showTint: Bool = true
    @State private var showMiniMap: Bool = true

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                if loading {
                    LoadingView(label: "Loading street view…")
                } else if let scene {
                    LookAroundRepresentable(scene: scene)
                        .ignoresSafeArea()
                } else if let error {
                    EmptyStateView(
                        title: "Street view unavailable",
                        caption: error,
                        systemImage: "binoculars"
                    )
                }

                if scene != nil {
                    heatTintOverlay
                    hudOverlay
                }
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        Toggle(isOn: $showTint) {
                            Label("Heat tint", systemImage: "drop.fill")
                        }
                        Toggle(isOn: $showMiniMap) {
                            Label("Mini heatmap", systemImage: "map.fill")
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "square.3.layers.3d.down.right")
                            Text("Layers")
                                .font(Theme.Font.monoCaption)
                                .tracking(0.6)
                        }
                        .foregroundStyle(.white)
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                        .foregroundStyle(.white)
                }
            }
            .toolbarBackground(.black.opacity(0.4), for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        }
        .task { await loadScene() }
    }

    @ViewBuilder
    private var heatTintOverlay: some View {
        if showTint {
            ZStack {
                LinearGradient(
                    colors: [tier.color.opacity(0.55), .clear, .clear, tier.color.opacity(0.45)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .blendMode(.plusLighter)
                .opacity(0.65)
                .ignoresSafeArea()

                LinearGradient(
                    colors: [.clear, tier.color.opacity(0.18), .clear],
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .blendMode(.softLight)
                .ignoresSafeArea()
            }
            .allowsHitTesting(false)
            .transition(.opacity)
        }
    }

    @ViewBuilder
    private var hudOverlay: some View {
        VStack(spacing: 0) {
            topHud
                .padding(.horizontal, Theme.Spacing.lg)
                .padding(.top, Theme.Spacing.sm)
                .allowsHitTesting(false)

            Spacer()
                .allowsHitTesting(false)

            HStack(alignment: .bottom) {
                bottomLabel
                    .allowsHitTesting(false)
                Spacer()
                    .allowsHitTesting(false)
                if showMiniMap {
                    miniHeatmap
                        .frame(width: 168, height: 168)
                        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.lg))
                        .overlay {
                            RoundedRectangle(cornerRadius: Theme.Radius.lg)
                                .stroke(tier.color.opacity(0.85), lineWidth: 1.2)
                        }
                        .shadow(color: tier.color.opacity(0.45), radius: 12, x: 0, y: 0)
                        .allowsHitTesting(false)
                        .transition(.scale.combined(with: .opacity))
                }
            }
            .padding(.horizontal, Theme.Spacing.lg)
            .padding(.bottom, Theme.Spacing.lg)
        }
    }

    private var topHud: some View {
        HStack(spacing: Theme.Spacing.sm) {
            HStack(spacing: 8) {
                Circle()
                    .fill(tier.color)
                    .frame(width: 8, height: 8)
                    .shadow(color: tier.color, radius: 6)
                Text(tier.rawValue.uppercased())
                    .font(Theme.Font.monoCaption)
                    .tracking(1.0)
                    .foregroundStyle(.white)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay {
                Capsule().stroke(tier.color.opacity(0.6), lineWidth: 0.8)
            }

            Spacer()

            HStack(spacing: 6) {
                Text("SCORE")
                    .font(Theme.Font.monoCaption)
                    .tracking(0.8)
                    .foregroundStyle(.white.opacity(0.7))
                Text(Format.score(score))
                    .font(.system(size: 18, weight: .semibold, design: .monospaced))
                    .foregroundStyle(tier.color)
                    .monospacedDigit()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay {
                Capsule().stroke(tier.color.opacity(0.6), lineWidth: 0.8)
            }
        }
    }

    private var bottomLabel: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(regionName)
                .font(Theme.Font.titleLarge)
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.7), radius: 6, y: 1)
            Text("LOOK AROUND · APPLE MAPS")
                .font(Theme.Font.monoCaption)
                .tracking(0.9)
                .foregroundStyle(.white.opacity(0.85))
                .shadow(color: .black.opacity(0.7), radius: 4, y: 1)
        }
    }

    private var miniHeatmap: some View {
        MiniHeatmap(
            polygons: polygons,
            selectedGeoid: selectedGeoid,
            center: coordinate
        )
    }

    private func loadScene() async {
        loading = true
        let request = MKLookAroundSceneRequest(coordinate: coordinate)
        do {
            let result = try await request.scene
            await MainActor.run {
                if let result {
                    self.scene = result
                } else {
                    self.error = "Apple's Look Around imagery isn't available at this location yet. Try a more central or recent address."
                }
                self.loading = false
            }
        } catch {
            await MainActor.run {
                self.error = error.localizedDescription
                self.loading = false
            }
        }
    }
}

struct LookAroundRepresentable: UIViewControllerRepresentable {
    let scene: MKLookAroundScene

    func makeUIViewController(context: Context) -> MKLookAroundViewController {
        let controller = MKLookAroundViewController(scene: scene)
        controller.isNavigationEnabled = true
        controller.showsRoadLabels = true
        controller.pointOfInterestFilter = .includingAll
        return controller
    }

    func updateUIViewController(_ controller: MKLookAroundViewController, context: Context) {
        controller.scene = scene
    }
}

struct MiniHeatmap: UIViewRepresentable {
    let polygons: [TractPolygon]
    let selectedGeoid: String
    let center: CLLocationCoordinate2D

    func makeUIView(context: Context) -> MKMapView {
        let view = MKMapView()
        view.overrideUserInterfaceStyle = .dark
        view.isUserInteractionEnabled = false
        view.isScrollEnabled = false
        view.isZoomEnabled = false
        view.isRotateEnabled = false
        view.isPitchEnabled = false
        view.showsCompass = false
        view.showsScale = false
        view.showsTraffic = false
        view.showsUserLocation = true
        view.delegate = context.coordinator

        let config = MKStandardMapConfiguration(elevationStyle: .flat, emphasisStyle: .muted)
        config.pointOfInterestFilter = .excludingAll
        view.preferredConfiguration = config

        let camera = MKMapCamera()
        camera.centerCoordinate = center
        camera.altitude = 1800
        camera.pitch = 0
        camera.heading = 0
        view.setCamera(camera, animated: false)

        renderOverlays(on: view)
        return view
    }

    func updateUIView(_ view: MKMapView, context: Context) {
        let camera = view.camera.copy() as? MKMapCamera ?? MKMapCamera()
        camera.centerCoordinate = center
        camera.altitude = 1800
        view.setCamera(camera, animated: true)
        renderOverlays(on: view)
    }

    private func renderOverlays(on view: MKMapView) {
        view.removeOverlays(view.overlays)
        let nearby = polygons
            .map { (poly: $0, dist: distance(from: $0.coordinates.first ?? Coordinate(latitude: 0, longitude: 0), to: center)) }
            .sorted { $0.dist < $1.dist }
            .prefix(40)
            .map(\.poly)

        for poly in nearby {
            let coords = poly.coordinates.map { $0.clLocation }
            let overlay = TractOverlay(coordinates: coords, count: coords.count)
            overlay.geoid = poly.geoid
            overlay.tier = poly.tier
            overlay.score = poly.score
            overlay.selected = poly.geoid == selectedGeoid
            view.addOverlay(overlay, level: .aboveLabels)
        }
    }

    private func distance(from a: Coordinate, to b: CLLocationCoordinate2D) -> Double {
        let dx = a.latitude - b.latitude
        let dy = a.longitude - b.longitude
        return dx * dx + dy * dy
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator: NSObject, MKMapViewDelegate {
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            guard let tract = overlay as? TractOverlay else { return MKOverlayRenderer(overlay: overlay) }
            let renderer = MKPolygonRenderer(polygon: tract)
            renderer.fillColor = tract.tier.uiColor.withAlphaComponent(tract.selected ? 0.78 : 0.45)
            renderer.strokeColor = tract.tier.uiColor.withAlphaComponent(tract.selected ? 1.0 : 0.7)
            renderer.lineWidth = tract.selected ? 2.0 : 0.8
            return renderer
        }
    }
}
