import SwiftUI

struct InterventionSlider: View {
    let intervention: Intervention
    @Binding var value: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(intervention.label)
                        .font(Theme.Font.title)
                        .foregroundStyle(Theme.Color.textPrimary)
                    Text(intervention.description)
                        .font(Theme.Font.label)
                        .foregroundStyle(Theme.Color.textSecondary)
                }
                Spacer()
                Text("\(Int(value.rounded())) \(intervention.unit)")
                    .font(Theme.Font.mono)
                    .foregroundStyle(Theme.Color.accent)
                    .monospacedDigit()
            }

            Slider(value: $value, in: intervention.minValue...intervention.maxValue)
                .tint(Theme.Color.accent)

            HStack {
                Text("\(Int(intervention.minValue))")
                Spacer()
                Text("default \(Int(intervention.defaultValue))")
                Spacer()
                Text("\(Int(intervention.maxValue))")
            }
            .font(Theme.Font.monoCaption)
            .foregroundStyle(Theme.Color.textMuted)
        }
    }
}
