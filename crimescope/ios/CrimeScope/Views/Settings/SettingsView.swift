import SwiftUI

struct SettingsView: View {
    @Environment(AppStore.self) private var store
    @Environment(APIClient.self) private var api
    @Environment(\.dismiss) private var dismiss

    @State private var apiURLDraft: String = ""
    @State private var probing: Bool = false
    @State private var probeResult: ProbeResult? = nil

    enum ProbeResult { case success, failed }

    private let cities: [(id: String, name: String, caption: String)] = [
        ("uk", "England & Wales (MSOA)",
         "7,200+ MSOAs · ONS Census 2021 + IMD/WIMD + data.police.uk")
    ]

    var body: some View {
        @Bindable var bindable = store
        Form {
            Section("BACKEND") {
                HStack {
                    Text("Status")
                    Spacer()
                    if store.usingMocks {
                        DemoBadge()
                    } else {
                        Text("LIVE")
                            .font(Theme.Font.monoCaption)
                            .tracking(0.7)
                            .foregroundStyle(Theme.Color.low)
                            .padding(.horizontal, 8).padding(.vertical, 3)
                            .background(Theme.Color.low.opacity(0.15), in: Capsule())
                    }
                }
                TextField("API base URL", text: $apiURLDraft, axis: .horizontal)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)

                HStack {
                    Button {
                        Task { await testURL() }
                    } label: {
                        if probing {
                            ProgressView().scaleEffect(0.8)
                        } else {
                            Text("Test connection")
                        }
                    }
                    .disabled(probing)

                    Spacer()

                    if let probeResult {
                        switch probeResult {
                        case .success:
                            Label("Reachable", systemImage: "checkmark.circle.fill")
                                .foregroundStyle(Theme.Color.low)
                        case .failed:
                            Label("Unreachable", systemImage: "xmark.octagon.fill")
                                .foregroundStyle(Theme.Color.high)
                        }
                    }
                }

                Button("Apply") {
                    Task {
                        bindable.apiBaseURL = apiURLDraft
                        await api.reprobe()
                    }
                }
                .disabled(apiURLDraft == store.apiBaseURL || apiURLDraft.isEmpty)
            }

            Section("CITY") {
                ForEach(cities, id: \.id) { city in
                    Button {
                        bindable.city = city.id
                    } label: {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(city.name)
                                    .foregroundStyle(Theme.Color.textPrimary)
                                Text(city.caption)
                                    .font(Theme.Font.label)
                                    .foregroundStyle(Theme.Color.textSecondary)
                            }
                            Spacer()
                            if store.city == city.id {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Theme.Color.accent)
                                    .padding(.top, 2)
                            }
                        }
                    }
                }
            }

            Section("PERSONA") {
                ForEach(Persona.allCases) { persona in
                    Button {
                        bindable.persona = persona
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(persona.displayName)
                                    .foregroundStyle(Theme.Color.textPrimary)
                                Text(persona.caption)
                                    .font(Theme.Font.label)
                                    .foregroundStyle(Theme.Color.textSecondary)
                            }
                            Spacer()
                            if store.persona == persona {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Theme.Color.accent)
                            }
                        }
                    }
                }
            }

            Section("ABOUT") {
                LabeledContent("Version", value: "0.1.0 (1)")
                LabeledContent("Build", value: "Native iOS · SwiftUI · MapKit")
            }

            Section {
                Button(role: .destructive) {
                    bindable.resetOnboarding()
                } label: {
                    Text("Reset onboarding")
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Done") { dismiss() }
                    .foregroundStyle(Theme.Color.accent)
            }
        }
        .onAppear { apiURLDraft = store.apiBaseURL }
    }

    private func testURL() async {
        probing = true
        probeResult = nil
        let originalURL = store.apiBaseURL
        store.apiBaseURL = apiURLDraft
        let reachable = await api.reprobe()
        store.apiBaseURL = originalURL
        await MainActor.run {
            probing = false
            probeResult = reachable ? .success : .failed
        }
    }
}
