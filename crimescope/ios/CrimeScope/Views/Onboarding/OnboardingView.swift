import SwiftUI

/// Single-screen onboarding — one decision (your role), then straight into
/// the map. Replaces the prior 4-step flow that put 30 seconds of marketing
/// copy between the user and their first answer.
struct OnboardingView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        @Bindable var bindable = store
        ZStack {
            Theme.Color.bg.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    header

                    VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                        Text("WHAT BEST DESCRIBES YOU?")
                            .font(Theme.Font.monoCaption)
                            .tracking(0.7)
                            .foregroundStyle(Theme.Color.textMuted)

                        VStack(spacing: Theme.Spacing.sm) {
                            ForEach(roles, id: \.persona) { role in
                                roleCard(role: role, selected: bindable.persona == role.persona) {
                                    bindable.persona = role.persona
                                }
                            }
                        }

                        Text("This shapes the recommendation copy. Same data underneath. You can change it anytime in Settings.")
                            .font(Theme.Font.label)
                            .foregroundStyle(Theme.Color.textMuted)
                    }

                    PrimaryButton(title: "Start exploring") {
                        bindable.hasOnboarded = true
                    }
                    .frame(maxWidth: .infinity)
                }
                .padding(Theme.Spacing.lg)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            Text("CrimeScope")
                .font(Theme.Font.display)
                .foregroundStyle(Theme.Color.textPrimary)
            Text("Explainable regional risk for England & Wales.")
                .font(Theme.Font.titleLarge)
                .foregroundStyle(Theme.Color.textSecondary)
            Text("Score, explain, project, compare, price — for any of 7,200+ MSOAs.")
                .font(Theme.Font.body)
                .foregroundStyle(Theme.Color.textMuted)
                .padding(.top, 2)
        }
    }

    // MARK: - Role rows

    private struct Role {
        let persona: Persona
        let icon: String
        let title: String
        let caption: String
    }

    private let roles: [Role] = [
        Role(persona: .insurance,
             icon: "doc.append",
             title: "Insurance",
             caption: "Premium guidance, surcharge bands, drivers behind the multiplier."),
        Role(persona: .real_estate,
             icon: "house.fill",
             title: "Real estate",
             caption: "Property pricing pressure, neighbourhood diligence, trend direction."),
        Role(persona: .publicSafety,
             icon: "shield.lefthalf.filled",
             title: "Public safety",
             caption: "Tactical review, deployment hints, blind-spot warnings."),
        Role(persona: .civic,
             icon: "person.3.fill",
             title: "Civic / curious",
             caption: "Plain-language summaries, no jargon, full transparency.")
    ]

    @ViewBuilder
    private func roleCard(role: Role, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: Theme.Spacing.md) {
                Image(systemName: role.icon)
                    .font(.system(size: 20, weight: .light))
                    .foregroundStyle(selected ? Theme.Color.accent : Theme.Color.textSecondary)
                    .frame(width: 28, height: 28)

                VStack(alignment: .leading, spacing: 2) {
                    Text(role.title)
                        .font(Theme.Font.title)
                        .foregroundStyle(Theme.Color.textPrimary)
                    Text(role.caption)
                        .font(Theme.Font.label)
                        .foregroundStyle(Theme.Color.textSecondary)
                }

                Spacer()

                if selected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Theme.Color.accent)
                }
            }
            .padding(Theme.Spacing.md)
            .background(Theme.Color.bgPanel, in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
            .overlay {
                RoundedRectangle(cornerRadius: Theme.Radius.lg)
                    .stroke(
                        selected ? Theme.Color.accent.opacity(0.5) : Theme.Color.border,
                        lineWidth: selected ? 1 : 0.5
                    )
            }
        }
    }
}
