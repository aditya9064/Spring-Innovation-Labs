import SwiftUI

struct LoadingView: View {
    var label: String? = nil

    var body: some View {
        VStack(spacing: 12) {
            ProgressView()
                .controlSize(.regular)
                .tint(Theme.Color.accent)
            if let label {
                Text(label)
                    .font(Theme.Font.label)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct EmptyStateView: View {
    let title: String
    var caption: String? = nil
    var systemImage: String = "tray"

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: systemImage)
                .font(.system(size: 26, weight: .light))
                .foregroundStyle(Theme.Color.textMuted)
            Text(title)
                .font(Theme.Font.title)
                .foregroundStyle(Theme.Color.textPrimary)
            if let caption {
                Text(caption)
                    .font(Theme.Font.body)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Theme.Color.textSecondary)
                    .padding(.horizontal)
            }
        }
        .padding(28)
        .frame(maxWidth: .infinity)
    }
}

struct DemoBadge: View {
    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Theme.Color.elevated)
                .frame(width: 6, height: 6)
                .overlay {
                    Circle()
                        .stroke(Theme.Color.elevated.opacity(0.4), lineWidth: 4)
                        .scaleEffect(1.6)
                }
            Text("DEMO DATA")
                .font(Theme.Font.monoCaption)
                .tracking(1.2)
                .foregroundStyle(Theme.Color.elevated)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(Theme.Color.elevated.opacity(0.12), in: RoundedRectangle(cornerRadius: Theme.Radius.pill))
        .overlay {
            RoundedRectangle(cornerRadius: Theme.Radius.pill)
                .stroke(Theme.Color.elevated.opacity(0.3), lineWidth: 0.5)
        }
    }
}

struct LiveBadge: View {
    var label: String = "LIVE"

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Theme.Color.low)
                .frame(width: 6, height: 6)
            Text(label)
                .font(Theme.Font.monoCaption)
                .tracking(1.2)
                .foregroundStyle(Theme.Color.low)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(Theme.Color.low.opacity(0.12), in: RoundedRectangle(cornerRadius: Theme.Radius.pill))
        .overlay {
            RoundedRectangle(cornerRadius: Theme.Radius.pill)
                .stroke(Theme.Color.low.opacity(0.3), lineWidth: 0.5)
        }
    }
}

struct DataSourceBadge: View {
    @Environment(AppStore.self) private var store
    var liveLabel: String = "LIVE"

    var body: some View {
        if store.usingMocks {
            DemoBadge()
        } else {
            LiveBadge(label: liveLabel)
        }
    }
}
