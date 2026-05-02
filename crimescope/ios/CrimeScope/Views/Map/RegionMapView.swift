import SwiftUI
import MapKit

final class TractOverlay: MKPolygon {
    var geoid: String = ""
    var tier: RiskTier = .moderate
    var score: Double = 0
    var selected: Bool = false
}

enum MapMode: String, CaseIterable {
    case threeD = "3D"
    case twoD = "2D"
}

struct RegionMapView: UIViewRepresentable {
    let polygons: [TractPolygon]
    let allowedTiers: Set<RiskTier>
    let selectedGeoid: String?
    let selectedCoordinate: CLLocationCoordinate2D?
    let userCoordinate: CLLocationCoordinate2D?
    var recenterNonce: Int = 0
    let mode: MapMode
    var defaultCenter: CLLocationCoordinate2D = MockData.ukCenter
    var defaultAltitude2D: Double = 1_400_000
    let onSelect: (String) -> Void

    func makeUIView(context: Context) -> MKMapView {
        let view = MKMapView()
        view.delegate = context.coordinator
        view.overrideUserInterfaceStyle = .dark
        view.showsCompass = true
        view.showsScale = false
        view.showsTraffic = false
        view.isPitchEnabled = true
        view.isRotateEnabled = true
        view.showsBuildings = true
        view.showsUserLocation = true

        applyConfiguration(to: view)
        // Always frame the city on first appearance — never the GPS location.
        // The user can press the location pill to recenter on themselves.
        applyCamera(to: view, mode: mode, coordinate: nil, animated: false)
        context.coordinator.lastDefaultCenter = defaultCenter
        context.coordinator.lastRecenterNonce = recenterNonce

        let tap = UITapGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handleTap(_:))
        )
        view.addGestureRecognizer(tap)

        return view
    }

    func updateUIView(_ view: MKMapView, context: Context) {
        // City switch — refly to the new city's default frame.
        let centerChanged = context.coordinator.lastDefaultCenter.map {
            $0.latitude != defaultCenter.latitude || $0.longitude != defaultCenter.longitude
        } ?? true
        if centerChanged {
            context.coordinator.lastDefaultCenter = defaultCenter
            context.coordinator.lastSelectedGeoid = nil
            applyCamera(to: view, mode: mode, coordinate: nil, animated: true)
        } else if context.coordinator.lastMode != mode {
            context.coordinator.lastMode = mode
            let target = selectedCoordinate ?? userCoordinate
            applyCamera(to: view, mode: mode, coordinate: target, animated: true)
        }

        // Recenter-on-user is now ONLY triggered by the explicit location button.
        if recenterNonce != context.coordinator.lastRecenterNonce,
           let user = userCoordinate {
            context.coordinator.lastRecenterNonce = recenterNonce
            flyTo(coordinate: user, in: view, mode: mode)
        }

        if let coord = selectedCoordinate,
           context.coordinator.lastSelectedGeoid != selectedGeoid {
            context.coordinator.lastSelectedGeoid = selectedGeoid
            flyTo(coordinate: coord, in: view, mode: mode)
        }

        view.removeOverlays(view.overlays)
        let visible = polygons.filter { allowedTiers.contains($0.tier) }
        for poly in visible {
            let coords = poly.coordinates.map { $0.clLocation }
            let overlay = TractOverlay(coordinates: coords, count: coords.count)
            overlay.geoid = poly.geoid
            overlay.tier = poly.tier
            overlay.score = poly.score
            overlay.selected = poly.geoid == selectedGeoid
            view.addOverlay(overlay, level: .aboveLabels)
        }
    }

    private func applyConfiguration(to view: MKMapView) {
        let config = MKStandardMapConfiguration(
            elevationStyle: .realistic,
            emphasisStyle: .muted
        )
        config.pointOfInterestFilter = MKPointOfInterestFilter(including: [
            .park, .hospital, .police, .fireStation, .school, .university
        ])
        config.showsTraffic = false
        view.preferredConfiguration = config
    }

    private func applyCamera(
        to view: MKMapView,
        mode: MapMode,
        coordinate: CLLocationCoordinate2D?,
        animated: Bool
    ) {
        let center = coordinate ?? defaultCenter
        let camera = MKMapCamera()
        camera.centerCoordinate = center
        switch mode {
        case .threeD:
            // Use a wide regional altitude when no specific coordinate is
            // given (so e.g. all of England & Wales fits), and a tight one
            // when the user/selection has a precise location.
            camera.altitude = coordinate == nil ? max(defaultAltitude2D * 0.8, 5500) : 1800
            camera.pitch = coordinate == nil ? 0 : 65
            camera.heading = coordinate == nil ? 0 : 30
        case .twoD:
            camera.altitude = coordinate == nil ? defaultAltitude2D : 8000
            camera.pitch = 0
            camera.heading = 0
        }
        if animated {
            UIView.animate(withDuration: 0.7) {
                view.setCamera(camera, animated: false)
            }
        } else {
            view.setCamera(camera, animated: false)
        }
    }

    private func flyTo(
        coordinate: CLLocationCoordinate2D,
        in view: MKMapView,
        mode: MapMode
    ) {
        let camera = MKMapCamera()
        camera.centerCoordinate = coordinate
        switch mode {
        case .threeD:
            camera.altitude = 900
            camera.pitch = 70
            camera.heading = view.camera.heading
        case .twoD:
            camera.altitude = 4500
            camera.pitch = 0
            camera.heading = 0
        }
        view.setCamera(camera, animated: true)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(parent: self)
    }

    final class Coordinator: NSObject, MKMapViewDelegate {
        let parent: RegionMapView
        var lastMode: MapMode = .threeD
        var lastSelectedGeoid: String?
        var lastRecenterNonce: Int = 0
        var lastDefaultCenter: CLLocationCoordinate2D?

        init(parent: RegionMapView) {
            self.parent = parent
            self.lastMode = parent.mode
        }

        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            guard let tract = overlay as? TractOverlay else {
                return MKOverlayRenderer(overlay: overlay)
            }
            let renderer = MKPolygonRenderer(polygon: tract)
            renderer.fillColor = tract.tier.uiColor.withAlphaComponent(tract.selected ? 0.50 : 0.22)
            renderer.strokeColor = tract.tier.uiColor.withAlphaComponent(tract.selected ? 1.0 : 0.65)
            renderer.lineWidth = tract.selected ? 2.5 : 1.0
            return renderer
        }

        @objc func handleTap(_ gesture: UITapGestureRecognizer) {
            guard let mapView = gesture.view as? MKMapView else { return }
            let point = gesture.location(in: mapView)
            let coordinate = mapView.convert(point, toCoordinateFrom: mapView)
            let mapPoint = MKMapPoint(coordinate)

            for overlay in mapView.overlays {
                guard let tract = overlay as? TractOverlay else { continue }
                let renderer = MKPolygonRenderer(polygon: tract)
                let viewPoint = renderer.point(for: mapPoint)
                if renderer.path?.contains(viewPoint) == true {
                    parent.onSelect(tract.geoid)
                    let generator = UIImpactFeedbackGenerator(style: .light)
                    generator.impactOccurred()
                    return
                }
            }
        }
    }
}
