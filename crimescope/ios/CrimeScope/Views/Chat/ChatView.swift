import SwiftUI

struct ChatView: View {
    let geoid: String?
    let regionName: String?

    @Environment(APIClient.self) private var api
    @Environment(\.dismiss) private var dismiss

    @State private var messages: [ChatMessage] = []
    @State private var input: String = ""
    @State private var sending: Bool = false
    @FocusState private var fieldFocused: Bool

    init(geoid: String? = nil, regionName: String? = nil) {
        self.geoid = geoid
        self.regionName = regionName
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        VStack(spacing: Theme.Spacing.md) {
                            grounding
                            ForEach(messages) { message in
                                bubble(message)
                                    .id(message.id)
                            }
                            if sending {
                                HStack {
                                    typingDots
                                    Spacer()
                                }
                                .padding(.leading, Theme.Spacing.lg)
                            }
                        }
                        .padding(Theme.Spacing.lg)
                    }
                    .onChange(of: messages.count) {
                        if let last = messages.last {
                            withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                        }
                    }
                }

                inputBar
            }
            .background(Theme.Color.bg)
            .navigationTitle("Ask CrimeScope")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private var grounding: some View {
        Card(background: Theme.Color.accent.opacity(0.08)) {
            VStack(alignment: .leading, spacing: 4) {
                Text("GROUNDED IN")
                    .font(Theme.Font.monoCaption)
                    .tracking(0.7)
                    .foregroundStyle(Theme.Color.textMuted)
                Text(regionName ?? "City-wide context")
                    .font(Theme.Font.title)
                    .foregroundStyle(Theme.Color.textPrimary)
                Text("I'll only summarize data CrimeScope already shows. Ask about drivers, trust, live disagreement, or peer comparison.")
                    .font(Theme.Font.label)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
    }

    private func bubble(_ message: ChatMessage) -> some View {
        HStack {
            if message.role == .user { Spacer(minLength: 60) }
            Text(message.text)
                .font(Theme.Font.body)
                .foregroundStyle(message.role == .user ? Theme.Color.bg : Theme.Color.textPrimary)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(message.role == .user ? Theme.Color.accent : Theme.Color.bgPanel,
                            in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
            if message.role == .assistant { Spacer(minLength: 60) }
        }
    }

    private var typingDots: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { i in
                Circle()
                    .fill(Theme.Color.textMuted)
                    .frame(width: 6, height: 6)
                    .opacity(0.4)
                    .animation(.easeInOut(duration: 0.6).repeatForever().delay(Double(i) * 0.15), value: sending)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Theme.Color.bgPanel, in: RoundedRectangle(cornerRadius: Theme.Radius.lg))
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("Ask about \(regionName ?? "this region")…", text: $input, axis: .vertical)
                .lineLimit(1...4)
                .focused($fieldFocused)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Theme.Color.bgPanel, in: RoundedRectangle(cornerRadius: Theme.Radius.md))
                .foregroundStyle(Theme.Color.textPrimary)

            Button {
                Task { await send() }
            } label: {
                Image(systemName: "arrow.up")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Theme.Color.bg)
                    .padding(10)
                    .background(input.trimmingCharacters(in: .whitespaces).isEmpty ? Theme.Color.borderStrong : Theme.Color.accent, in: Circle())
            }
            .disabled(input.trimmingCharacters(in: .whitespaces).isEmpty || sending)
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Color.bg)
    }

    private func send() async {
        let text = input.trimmingCharacters(in: .whitespaces)
        guard !text.isEmpty else { return }
        let userMessage = ChatMessage(id: UUID(), role: .user, text: text, createdAt: Date())
        messages.append(userMessage)
        input = ""
        sending = true
        let response = await api.sendChat(message: text, geoid: geoid)
        await MainActor.run {
            messages.append(ChatMessage(id: UUID(), role: .assistant, text: response, createdAt: Date()))
            sending = false
        }
    }
}
