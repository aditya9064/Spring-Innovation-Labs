import SwiftUI

struct Card<Content: View>: View {
    var padding: CGFloat = Theme.Spacing.lg
    var background: Color = Theme.Color.bgPanel
    @ViewBuilder var content: () -> Content

    var body: some View {
        content()
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(background, in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
            .overlay {
                RoundedRectangle(cornerRadius: Theme.Radius.lg)
                    .stroke(Theme.Color.border, lineWidth: 0.5)
            }
    }
}

struct SectionHeader: View {
    let title: String
    var caption: String? = nil
    var trailing: AnyView? = nil

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title.uppercased())
                    .font(Theme.Font.monoCaption)
                    .foregroundStyle(Theme.Color.textMuted)
                    .tracking(0.7)
                if let caption {
                    Text(caption)
                        .font(Theme.Font.label)
                        .foregroundStyle(Theme.Color.textSecondary)
                }
            }
            Spacer()
            if let trailing { trailing }
        }
    }
}
