import SwiftUI

struct PrimaryButton: View {
    let title: String
    var systemImage: String? = nil
    var role: ButtonRole? = nil
    let action: () -> Void

    var body: some View {
        Button(role: role, action: action) {
            HStack(spacing: 8) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
                    .font(Theme.Font.title)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(Theme.Color.accent, in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
            .foregroundStyle(Theme.Color.bg)
        }
    }
}

struct SecondaryButton: View {
    let title: String
    var systemImage: String? = nil
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
                    .font(Theme.Font.label)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Theme.Color.bgRaised, in: RoundedRectangle(cornerRadius: Theme.Radius.md))
            .foregroundStyle(Theme.Color.textPrimary)
            .overlay {
                RoundedRectangle(cornerRadius: Theme.Radius.md)
                    .stroke(Theme.Color.border, lineWidth: 0.5)
            }
        }
    }
}

struct GhostButton: View {
    let title: String
    var systemImage: String? = nil
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
                    .font(Theme.Font.label)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .foregroundStyle(Theme.Color.accent)
        }
    }
}
