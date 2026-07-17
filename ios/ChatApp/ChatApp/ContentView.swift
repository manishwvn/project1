//
//  ContentView.swift
//  ChatApp
//
//  Created by Manish on 7/17/26.
//

import SwiftUI

struct ChatRequest: Encodable {
    let message: String
}

struct ChatResponse: Decodable {
    let reply: String
}

struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
}

struct MessageSegment: Identifiable {
    let id = UUID()
    let text: String
    let isCode: Bool
}

func parseSegments(_ text: String) -> [MessageSegment] {
    let parts = text.components(separatedBy: "```")
    return parts.enumerated().compactMap { index, part in
        let trimmed = part.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let isCode = index % 2 == 1
        if isCode {
            let lines = trimmed.split(separator: "\n", maxSplits: 1, omittingEmptySubsequences: false)
            let body = lines.count > 1 && !lines[0].contains(" ") ? String(lines[1]) : trimmed
            return MessageSegment(text: body, isCode: true)
        }
        return MessageSegment(text: trimmed, isCode: false)
    }
}

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack {
            if message.isUser { Spacer(minLength: 40) }

            VStack(alignment: .leading, spacing: 6) {
                ForEach(parseSegments(message.text)) { segment in
                    if segment.isCode {
                        Text(segment.text)
                            .font(.system(.footnote, design: .monospaced))
                            .padding(8)
                            .background(Color.black.opacity(0.85))
                            .foregroundColor(.white)
                            .cornerRadius(8)
                    } else {
                        Text((try? AttributedString(markdown: segment.text)) ?? AttributedString(segment.text))
                    }
                }
            }
            .padding(10)
            .background(message.isUser ? Color.blue : Color(.systemGray5))
            .foregroundColor(message.isUser ? .white : .primary)
            .cornerRadius(16)

            if !message.isUser { Spacer(minLength: 40) }
        }
    }
}

struct ContentView: View {
    @State private var message: String = ""
    @State private var messages: [ChatMessage] = []
    @State private var isLoading: Bool = false
    @FocusState private var isFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(messages) { msg in
                            MessageBubble(message: msg)
                                .id(msg.id)
                        }
                        if isLoading {
                            HStack {
                                ProgressView()
                                Spacer()
                            }
                        }
                    }
                    .padding()
                }
                .onTapGesture {
                    isFocused = false
                }
                .onChange(of: messages.count) {
                    if let last = messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }

            Divider()

            HStack {
                TextField("Type a message", text: $message)
                    .textFieldStyle(.roundedBorder)
                    .focused($isFocused)
                    .submitLabel(.send)
                    .onSubmit { sendMessage() }

                Button("Send") {
                    sendMessage()
                }
                .disabled(message.trimmingCharacters(in: .whitespaces).isEmpty || isLoading)
            }
            .padding()
        }
    }

    func sendMessage() {
        let userText = message.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !userText.isEmpty, let url = URL(string: "http://192.168.1.101:8000/chat") else { return }

        messages.append(ChatMessage(text: userText, isUser: true))
        message = ""

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONEncoder().encode(ChatRequest(message: userText))

        isLoading = true

        URLSession.shared.dataTask(with: request) { data, _, error in
            DispatchQueue.main.async {
                isLoading = false
                guard let data = data, error == nil,
                      let decoded = try? JSONDecoder().decode(ChatResponse.self, from: data) else {
                    messages.append(ChatMessage(text: "Error: could not reach backend", isUser: false))
                    return
                }
                messages.append(ChatMessage(text: decoded.reply, isUser: false))
            }
        }.resume()
    }
}

#Preview {
    ContentView()
}
