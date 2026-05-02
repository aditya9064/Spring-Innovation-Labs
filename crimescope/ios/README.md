# CrimeScope iOS

Native iOS app for explainable regional risk — Chicago tract-level scoring, trust passport, verified-vs-live disagreement, drivers, persona-specific decisions, simulator, audit trail, and challenge mode.

100% native — **SwiftUI, MapKit, PDFKit, Swift Concurrency** — no Expo, no React Native, no third-party dependencies.

> **Mocks-first.** The app ships with a complete bundled mock layer (50 Chicago tracts, hex-tile polygons, live events, audit + challenges). It auto-detects whether the FastAPI backend at the configured URL is reachable and falls back to mocks transparently. A "Demo Data" badge appears whenever mocks are active.

---

## Stack

- **iOS 17.0+**, Swift 5.10
- **SwiftUI** for all UI, **`@Observable`** state (`AppStore`, `AuditStore`, `ChallengeStore`, `LiveTicker`, `APIClient`)
- **MapKit** + `UIViewRepresentable` for tract polygon overlays with tier-colored `MKPolygonRenderer` and tap detection
- **PDFKit** + `UIGraphicsPDFRenderer` for report export, native iOS share sheet via `ShareLink`
- **URLSession + Codable** for networking with automatic mock fallback per endpoint
- **`UserDefaults`** persistence for app state, audit log, and challenge log
- **Zero third-party dependencies** — no SPM packages required
- **XcodeGen** to regenerate `CrimeScope.xcodeproj` from `project.yml` (avoids merge conflicts on the `.pbxproj`)

---

## Run it

> Requirements: macOS 14+, **Xcode 15.4+** (Xcode 26 verified), iOS 17 simulator (or a real device on iOS 17+), [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)

```bash
cd crimescope/ios

# 1. Install XcodeGen if you haven't already
brew install xcodegen

# 2. Generate the .xcodeproj from project.yml
xcodegen generate

# 3. Open in Xcode
open CrimeScope.xcodeproj
```

The `.xcodeproj` is gitignored — regenerate it any time `project.yml` changes (or after a fresh clone).

### Run on the simulator

In Xcode:
1. Select an iPhone 15/16 simulator (or any iPhone running iOS 17+) from the run-destination dropdown.
2. ⌘R to build & run.

The app starts in dark mode, runs onboarding on first launch, and opens with mock data backing every screen ("DEMO DATA" badge visible).

### Build & run on **your iPhone**

The fast path:

1. **Plug your iPhone into your Mac** with a USB-C / Lightning cable.
2. On the phone, tap **Trust this computer** when prompted, and unlock the device.
3. (One-time, iOS 16+) Enable Developer Mode on the phone:
   `Settings → Privacy & Security → Developer Mode → On → Restart`. After reboot, confirm the prompt.
4. In Xcode, pick your device from the run-destination dropdown (top toolbar — it should show your iPhone's name with a small device icon, *not* "Any iOS Device").
5. ⌘R. Xcode will compile, sign, install, and launch the app on your phone.
6. **First launch only** — iOS will refuse to open the app until you trust the developer certificate:
   `Settings → General → VPN & Device Management → Developer App → "Apple Development: <your-account>" → Trust`.
   Then re-launch the app from the home screen.

#### Signing — already wired in `project.yml`

```yaml
settings:
  base:
    DEVELOPMENT_TEAM: NCHGWJQY94          # your Apple Developer team ID
    CODE_SIGN_STYLE: Automatic
    CODE_SIGN_IDENTITY: "Apple Development"
targets:
  CrimeScope:
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.crimescope.app
```

If you need to change team or bundle ID:

- Edit `project.yml` (`DEVELOPMENT_TEAM` and/or `PRODUCT_BUNDLE_IDENTIFIER`).
- Re-run `xcodegen generate`.
- Re-open the project in Xcode.

You can find your team ID under [developer.apple.com → Account → Membership](https://developer.apple.com/account#MembershipDetailsCard). A free Apple ID also works for on-device installs (limited to 7-day signing and 3 sideloaded apps); paid Apple Developer Program enrollment ($99/yr) lifts those limits.

#### Common on-device gotchas

| Symptom | Fix |
|---|---|
| `Signing for "CrimeScope" requires a development team` | Set `DEVELOPMENT_TEAM` in `project.yml`, re-run `xcodegen generate`. |
| `Failed to register bundle identifier ... already in use` | Bundle ID `com.crimescope.app` is taken on Apple's side by another team. Change `PRODUCT_BUNDLE_IDENTIFIER` to something unique (e.g. `com.<yourname>.crimescope`) and regenerate. |
| `Could not launch "CrimeScope" — Untrusted Developer` | Trust the cert on-device under **Settings → General → VPN & Device Management**. |
| Device not showing in dropdown | Unplug, replug, accept Trust prompt; ensure iOS ≥ 17 and Developer Mode is on. |
| `xcodegen: command not found` | `brew install xcodegen`. |

### Connect to the local FastAPI backend (optional — the app runs fully on mocks)

Start the backend:

```bash
# In another terminal
cd crimescope/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Find your Mac's LAN IP:

```bash
ipconfig getifaddr en0    # Wi-Fi
# or
ipconfig getifaddr en1    # Ethernet / Thunderbolt
```

In the app, go to **More → Settings → API base URL**, enter `http://<your-mac-lan-ip>:8000`, tap **Test connection**, then **Apply**. The app probes `/api/health`, flips to live data, and replaces the `DEMO DATA` badge with `LIVE`.

> The simulator can use `http://localhost:8000` directly. A physical device needs your Mac's LAN IP. Both Mac and iPhone must be on the same Wi-Fi network. `NSAllowsLocalNetworking` and `NSAllowsArbitraryLoads` are already declared in `Info.plist` so HTTP works in dev.

---

## Feature map

### Phase 1 — core decision-support
- **Onboarding** — 4-step flow: explainer, city, persona, trust model.
- **Map tab** — MapKit (`MKMapView`) with tract polygons rendered via `MKPolygonRenderer`, tier-colored fills, tap to select; KPI strip (regions / critical / high / avg), tier filter chips, search modal, legend.
- **Region Sheet** — bottom sheet (`.sheet` + `.presentationDetents`) with score header (overall / violent / property), baseline-vs-ML delta, **Disagreement banner**, **Trust Passport** (confidence/completeness/freshness/source agreement/underreporting/recommended action), **What Changed**, **Drivers** (direction + impact + evidence), **Persona Decision card** with override path. Action grid jumps to simulator, compare, report, audit, challenge, chat.
- **Live tab** — citywide pulse banner (verified/pending/unverified counts) and a stream of `LiveEventRow`s with NEW pulse badge. Mock ticker injects a fresh event every ~35s (`Timer` + `LiveTicker`).
- **Reports tab** — searchable list, full report detail (executive summary, narrative, trust notes, drivers, peer comparison, challenges), one-tap **PDF export** via `UIGraphicsPDFRenderer`, share sheet via `ShareLink`.

### Phase 2 — differentiators
- **Compare** — pick two regions, see side-by-side score / trust / live disagreement / persona recommendation. AI summary line at the top.
- **Simulator** — `Slider` per intervention (patrol density, lighting, youth programs, cameras, violence interruption); shows baseline → projected score with tier shift, narrative result, breakdown, **Log to audit** button.
- **Audit Trail** — chronological record with override badges and stats; new-entry modal as a `Form`; simulator commits create entries automatically.
- **Challenge Mode** — file structured challenges (data / model / decision / scope) with evidence and proposed adjustment slider (−20 / +20).
- **Blind Spots** — flagged regions with high underreporting risk; reason annotated.

### Phase 3 — supporting
- **AI Chat** — modal grounded in the currently-selected region. Mock responses cite the region's drivers, trust passport, and disagreement when no backend is reachable.
- **Settings** — backend URL test+apply (live probe), city, persona, reset onboarding.
- **More tab** — watchlist of starred regions + index of secondary screens.

---

## Architecture

```
ios/
├── project.yml                      # XcodeGen manifest — single source of truth
├── README.md
├── .gitignore
└── CrimeScope/
    ├── App/
    │   ├── CrimeScopeApp.swift      # @main entry, environment injection
    │   └── RootView.swift           # Onboarding gate + TabView
    ├── Models/
    │   ├── Contracts.swift          # All Codable types: TractScore, RiskTier, Persona, TrustPassport, RiskPackage, LiveEvent, AuditRecord, ChallengeRecord, …
    │   └── Format.swift             # Score / delta / time / tier helpers
    ├── Services/
    │   ├── AppStore.swift           # @Observable global state (UserDefaults-backed)
    │   ├── APIClient.swift          # URLSession + Codable + mock fallback per endpoint
    │   ├── MockData.swift           # 50 tracts, hex polygons, drivers, trust, live events, simulator math
    │   ├── LocalStores.swift        # AuditStore + ChallengeStore (UserDefaults persistence)
    │   ├── LiveTicker.swift         # Mock pulse + BlindSpots compute
    │   └── PDFRenderer.swift        # UIGraphicsPDFRenderer report export
    ├── Theme/
    │   └── Theme.swift              # Color / Font / Spacing / Radius tokens, RiskTier color extensions
    ├── Views/
    │   ├── Components/              # TierPill, ScoreNumber, DeltaPill, Card, SectionHeader, StatusViews (Loading/Empty/DemoBadge), Buttons, InterventionSlider
    │   ├── Onboarding/
    │   ├── Map/                     # RegionMapView (UIViewRepresentable), MapTab, MapAccessories (KPI/Filter/Legend/Search)
    │   ├── Region/                  # RegionSheet (composes ScoreHeader + Disagreement + TrustPassport + Drivers + WhatChanged + PersonaDecision + ActionsBar)
    │   ├── Live/
    │   ├── Reports/
    │   ├── Compare/                 # ComparePickerView + CompareDetailView
    │   ├── Simulator/
    │   ├── Audit/                   # AuditListView + AuditNewView
    │   ├── Challenge/               # ChallengeListView + ChallengeNewView
    │   ├── BlindSpots/
    │   ├── Chat/
    │   ├── Settings/
    │   └── More/
    └── Resources/
        ├── Info.plist
        └── Assets.xcassets/         # AppIcon, AccentColor, BackgroundPrimary
```

### Live-vs-mock fallback

`APIClient.probe()` hits `${apiBaseURL}/api/health` with a 1.5s timeout on launch. If the probe fails, every subsequent fetch returns the bundled mock equivalent without hitting the network. The store's `usingMocks` flag drives the "Demo Data" badge.

Per-endpoint try/catch means even partial backend failures fall back gracefully (so a broken `/api/compare` doesn't crash the rest of the app).

### Trust model in the UI

The whole app respects the same separation as the web frontend: the verified historical baseline and the ML-adjusted score are the score-of-record; live signals are surfaced separately. When they diverge, the **Disagreement banner** shows it explicitly with a Δ — never a silent override. The Trust Passport sits next to every recommendation.

---

## Design tokens

| Role | Color |
|---|---|
| Background | `#0a0a0a` |
| Panel | `#111` |
| Raised | `#1f1f1f` |
| Accent | `#00d4ff` |
| Critical | `#ff3b30` |
| High | `#ff9500` |
| Elevated | `#ffcc00` |
| Moderate | `#00d4ff` |
| Low | `#34c759` |

Type: SF Pro for sans, **SF Mono** for numerics / labels (system default, no font bundling required). Deployment target `iOS 17.0` to use `@Observable`, `NavigationStack`, modern `Map`, and `.presentationDetents`.

---

## Roadmap (post-MVP)

- Push notifications via `UserNotifications` framework for watchlist tracts crossing tier thresholds.
- `LocalAuthentication` (Face ID) gate for opening reports / persona decisions.
- Offline tile caching for the most-recent map view.
- App Intents + Siri shortcuts for "show me \[region\]" voice queries.
- Real WebSocket connection (`URLSessionWebSocketTask`) for live events when the backend exposes one.
- iPad split view + Mac Catalyst.
