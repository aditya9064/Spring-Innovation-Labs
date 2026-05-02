import SwiftUI
import MapKit

final class TractOverlay: MKPolygon {
    var geoid: String = ""
    var tier: RiskTier = .moderate
    var score: Double = 0
    var selected: Bool = false
    var searchHighlight: Bool = false
}

/// Sibling overlay rendered underneath a search-highlighted tract to fake a
/// CSS-style glow (MKPolygonRenderer has no shadow/blur, so we draw a wider,
/// translucent cyan stroke beneath the solid one).
final class SearchGlowOverlay: MKPolygon {
    var geoid: String = ""
}

/// Pulsing cyan annotation that mirrors the web `.cs-search-pin` element.
final class SearchPinAnnotation: NSObject, MKAnnotation {
    @objc dynamic var coordinate: CLLocationCoordinate2D
    init(coordinate: CLLocationCoordinate2D) {
        self.coordinate = coordinate
    }
}

final class SearchPinAnnotationView: MKAnnotationView {
    static let reuseId = "SearchPinAnnotationView"

    private let pulseLayer = CAShapeLayer()
    private let dotLayer = CAShapeLayer()

    override init(annotation: MKAnnotation?, reuseIdentifier: String?) {
        super.init(annotation: annotation, reuseIdentifier: reuseIdentifier)
        configure()
    }

    required init?(coder aDecoder: NSCoder) {
        super.init(coder: aDecoder)
        configure()
    }

    private func configure() {
        isUserInteractionEnabled = false
        canShowCallout = false
        frame = CGRect(x: 0, y: 0, width: 96, height: 96)
        centerOffset = .zero

        let cyan = UIColor(red: 0.0, green: 0.831, blue: 1.0, alpha: 1.0)

        // Pulse ring
        let pulseSize: CGFloat = 36
        pulseLayer.path = UIBezierPath(
            ovalIn: CGRect(x: 0, y: 0, width: pulseSize, height: pulseSize)
        ).cgPath
        pulseLayer.fillColor = cyan.withAlphaComponent(0.22).cgColor
        pulseLayer.strokeColor = cyan.cgColor
        pulseLayer.lineWidth = 2
        pulseLayer.bounds = CGRect(x: 0, y: 0, width: pulseSize, height: pulseSize)
        pulseLayer.position = CGPoint(x: bounds.midX, y: bounds.midY)
        pulseLayer.shadowColor = cyan.cgColor
        pulseLayer.shadowRadius = 12
        pulseLayer.shadowOpacity = 0.55
        pulseLayer.shadowOffset = .zero
        layer.addSublayer(pulseLayer)

        // Center dot
        let dotSize: CGFloat = 14
        dotLayer.path = UIBezierPath(
            ovalIn: CGRect(x: 0, y: 0, width: dotSize, height: dotSize)
        ).cgPath
        dotLayer.fillColor = cyan.cgColor
        dotLayer.strokeColor = UIColor.white.cgColor
        dotLayer.lineWidth = 2
        dotLayer.bounds = CGRect(x: 0, y: 0, width: dotSize, height: dotSize)
        dotLayer.position = CGPoint(x: bounds.midX, y: bounds.midY)
        dotLayer.shadowColor = cyan.cgColor
        dotLayer.shadowRadius = 8
        dotLayer.shadowOpacity = 0.9
        dotLayer.shadowOffset = .zero
        layer.addSublayer(dotLayer)
    }

    override func didMoveToSuperview() {
        super.didMoveToSuperview()
        guard superview != nil else {
            pulseLayer.removeAllAnimations()
            return
        }
        startPulsing()
    }

    private func startPulsing() {
        let scale = CABasicAnimation(keyPath: "transform.scale")
        scale.fromValue = 0.4
        scale.toValue = 2.6

        let opacity = CABasicAnimation(keyPath: "opacity")
        opacity.fromValue = 0.9
        opacity.toValue = 0.0

        let group = CAAnimationGroup()
        group.animations = [scale, opacity]
        group.duration = 1.6
        group.repeatCount = .infinity
        group.timingFunction = CAMediaTimingFunction(name: .easeOut)
        group.isRemovedOnCompletion = false

        pulseLayer.add(group, forKey: "cs-search-pulse")
    }
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
    /// Geoid of the region resolved from a search — gets a cyan glow border.
    var searchHighlightGeoid: String? = nil
    /// Coordinate where the search pin pulses (typically the resolved region's centroid).
    var searchHighlightCoordinate: CLLocationCoordinate2D? = nil
    /// Bumped each time a fresh search hit lands so the camera flies in tight.
    var searchNonce: Int = 0
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

        view.register(
            SearchPinAnnotationView.self,
            forAnnotationViewWithReuseIdentifier: SearchPinAnnotationView.reuseId
        )

        applyConfiguration(to: view)
        // Always frame the city on first appearance — never the GPS location.
        // The user can press the location pill to recenter on themselves.
        applyCamera(to: view, mode: mode, coordinate: nil, animated: false)
        context.coordinator.lastDefaultCenter = defaultCenter
        context.coordinator.lastRecenterNonce = recenterNonce
        context.coordinator.lastSearchNonce = searchNonce

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
            flyTo(coordinate: user, in: view, mode: mode, tight: false)
        }

        // Search hit — fly tight (mirrors web `searchZoom: 17`).
        if searchNonce != context.coordinator.lastSearchNonce,
           let coord = searchHighlightCoordinate {
            context.coordinator.lastSearchNonce = searchNonce
            flyTo(coordinate: coord, in: view, mode: mode, tight: true)
        } else if let coord = selectedCoordinate,
                  context.coordinator.lastSelectedGeoid != selectedGeoid {
            context.coordinator.lastSelectedGeoid = selectedGeoid
            flyTo(coordinate: coord, in: view, mode: mode, tight: false)
        }

        // Tract overlays.
        view.removeOverlays(view.overlays)
        let visible = polygons.filter { allowedTiers.contains($0.tier) }
        for poly in visible {
            let coords = poly.coordinates.map { $0.clLocation }
            // Glow goes UNDER so the bright stroke renders on top.
            if poly.geoid == searchHighlightGeoid {
                let glow = SearchGlowOverlay(coordinates: coords, count: coords.count)
                glow.geoid = poly.geoid
                view.addOverlay(glow, level: .aboveLabels)
            }
            let overlay = TractOverlay(coordinates: coords, count: coords.count)
            overlay.geoid = poly.geoid
            overlay.tier = poly.tier
            overlay.score = poly.score
            overlay.selected = poly.geoid == selectedGeoid
            overlay.searchHighlight = poly.geoid == searchHighlightGeoid
            view.addOverlay(overlay, level: .aboveLabels)
        }

        // Search pin annotation.
        let existingPins = view.annotations.compactMap { $0 as? SearchPinAnnotation }
        if let coord = searchHighlightCoordinate {
            let needsUpdate: Bool
            if let pin = existingPins.first {
                needsUpdate = pin.coordinate.latitude != coord.latitude
                    || pin.coordinate.longitude != coord.longitude
            } else {
                needsUpdate = true
            }
            if needsUpdate {
                view.removeAnnotations(existingPins)
                view.addAnnotation(SearchPinAnnotation(coordinate: coord))
            }
        } else if !existingPins.isEmpty {
            view.removeAnnotations(existingPins)
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
        mode: MapMode,
        tight: Bool
    ) {
        let camera = MKMapCamera()
        camera.centerCoordinate = coordinate
        switch mode {
        case .threeD:
            camera.altitude = tight ? 450 : 900
            camera.pitch = 70
            camera.heading = view.camera.heading
        case .twoD:
            camera.altitude = tight ? 1500 : 4500
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
        var lastSearchNonce: Int = 0
        var lastDefaultCenter: CLLocationCoordinate2D?

        init(parent: RegionMapView) {
            self.parent = parent
            self.lastMode = parent.mode
        }

        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            let cyan = UIColor(red: 0.0, green: 0.831, blue: 1.0, alpha: 1.0)

            if let glow = overlay as? SearchGlowOverlay {
                let renderer = MKPolygonRenderer(polygon: glow)
                renderer.fillColor = .clear
                renderer.strokeColor = cyan.withAlphaComponent(0.55)
                renderer.lineWidth = 10
                renderer.lineJoin = .round
                renderer.lineCap = .round
                return renderer
            }
            guard let tract = overlay as? TractOverlay else {
                return MKOverlayRenderer(overlay: overlay)
            }
            let renderer = MKPolygonRenderer(polygon: tract)
            if tract.searchHighlight {
                renderer.fillColor = cyan.withAlphaComponent(0.18)
                renderer.strokeColor = cyan
                renderer.lineWidth = 3.5
            } else {
                renderer.fillColor = tract.tier.uiColor.withAlphaComponent(tract.selected ? 0.50 : 0.22)
                renderer.strokeColor = tract.tier.uiColor.withAlphaComponent(tract.selected ? 1.0 : 0.65)
                renderer.lineWidth = tract.selected ? 2.5 : 1.0
            }
            return renderer
        }

        func mapView(_ mapView: MKMapView, viewFor annotation: MKAnnotation) -> MKAnnotationView? {
            if annotation is SearchPinAnnotation {
                let view = mapView.dequeueReusableAnnotationView(
                    withIdentifier: SearchPinAnnotationView.reuseId,
                    for: annotation
                )
                return view
            }
            return nil
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
