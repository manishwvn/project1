import { useRef, useState, useEffect } from "react";
import "./App.css";

type Role = "user" | "assistant";

interface Message {
  role: Role;
  content: string;
}

interface Thread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function App() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createNewThread();
  }, []);

  async function loadThreads() {
    try {
      console.log("Attempting to fetch from:", `${API_URL}/threads`);
      const res = await fetch(`${API_URL}/threads`);
      console.log("Threads response received:", res.status, res.ok);
      if (!res.ok) {
        console.error("Response not ok:", res.status);
        throw new Error(`Backend returned ${res.status}`);
      }
      const text = await res.text();
      console.log("Response text:", text);
      const data: Thread[] = JSON.parse(text);
      console.log("Threads loaded:", data.length, "threads");
      setThreads(data);
      if (data.length > 0 && !currentThreadId) {
        setCurrentThreadId(data[0].id);
        await loadThreadMessages(data[0].id);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("Failed to load threads - Error:", msg);
    }
  }

  async function loadThreadMessages(threadId: string) {
    try {
      const res = await fetch(`${API_URL}/threads/${threadId}`);
      if (!res.ok) throw new Error("Failed to load messages");
      const data: Message[] = await res.json();
      setMessages(data);
    } catch (err) {
      console.error("Failed to load messages:", err);
    }
  }

  async function createNewThread() {
    try {
      const res = await fetch(`${API_URL}/threads`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to create thread");
      const newThread: Thread = await res.json();
      setThreads((prev) => [newThread, ...prev]);
      setCurrentThreadId(newThread.id);
      setMessages([]);
    } catch (err) {
      setError("Failed to create new thread");
    }
  }

  async function switchThread(threadId: string) {
    setCurrentThreadId(threadId);
    await loadThreadMessages(threadId);
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading || !currentThreadId) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, thread_id: currentThreadId }),
      });

      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = "";
      let messageAdded = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const eventData = JSON.parse(line.slice(6));
            if (eventData.type === "token") {
              assistantMessage += eventData.content;
              if (!messageAdded) {
                setMessages((prev) => [
                  ...prev,
                  { role: "assistant", content: assistantMessage },
                ]);
                messageAdded = true;
              } else {
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1].content = assistantMessage;
                  return updated;
                });
              }
            }
          }
        }
      }
      await loadThreads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") sendMessage();
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-top">Agent Chat</div>
        <div className="thread-controls">
          <select
            value={currentThreadId || ""}
            onChange={(e) => switchThread(e.target.value)}
            disabled={loading}
            className="thread-select"
          >
            {threads.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
          <button onClick={createNewThread} disabled={loading} className="new-thread-btn">
            + New
          </button>
        </div>
      </header>

      <div className="messages">
        {messages.length === 0 && (
          <div className="empty">Ask the agent something — try "2 + 2" or "what's the weather in Tokyo"</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
        {loading && <div className="bubble assistant loading">…</div>}
        {error && <div className="bubble error">Error: {error}</div>}
        <div ref={bottomRef} />
      </div>

      <div className="input-bar">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message"
          disabled={loading || !currentThreadId}
        />
        <button onClick={sendMessage} disabled={loading || !input.trim() || !currentThreadId}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;
