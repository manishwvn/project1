# project1 — Agentic AI Chat with Streaming + Memory

Fast-learning build of an agentic AI stack with real-time streaming responses and persistent conversation memory. Backend: FastAPI + LangGraph + Groq. Frontend: React + Vite. Database: SQLite.

## Current State

### Completed
- LangGraph agent with tool calling (calculator, weather API)
- Streaming endpoint (`/chat/stream`) with SSE + Server-Sent Events
- Frontend real-time token display (token-by-token accumulation)
- Backward-compatible blocking endpoint (`/chat`)
- Full agent loop: reasoning → tool calls → tool execution → streaming results
- **Conversation memory**: Thread-based message persistence (SQLite)
- **Thread management**: Create, switch, list conversations independently

### Architecture

**Backend** (`backend/main.py`):
- Chat endpoints:
  - `POST /chat` — blocking, returns `{"reply": "...", "thread_id": "..."}` (updated with thread_id)
  - `POST /chat/stream` — SSE, streams tokens + thread_id at end
- Thread management endpoints:
  - `GET /threads` — list all conversations
  - `GET /threads/{id}` — load message history for thread
  - `POST /threads` — create new conversation
  - `DELETE /threads/{id}` — delete thread and messages
- Uses `agent.astream()` with `stream_mode=["messages", "updates"]` and `version="v2"`
- Loads previous messages per thread, passes to agent as context

**Database** (`backend/db.py`):
- SQLAlchemy ORM with SQLite backend (`backend/chat.db`)
- Models: `Thread` (id, title, created_at, updated_at), `Message` (id, thread_id, role, content, created_at)
- Auto-persists user + assistant messages after each request
- On thread switch: loads all messages, reconstructs LangChain message list

**Frontend** (`frontend/src/App.tsx`):
- Thread dropdown + "New" button for conversation management
- `loadThreads()` — fetch thread list, populate dropdown
- `switchThread()` — load messages for selected thread
- `sendMessage()` — include `thread_id` in request, receive new `thread_id` if needed
- Streams responses same as before, full history visible after switch

**Agent** (`backend/agent.py`):
- StateGraph with nodes: `chat` (LLM), `tools` (tool execution)
- Conditional routing: loop back to chat if tool calls present, else END
- Tools: `calculator` (math), `get_weather` (OpenWeatherMap API)

### Tech Stack
- Backend: FastAPI (uvicorn), LangGraph (v0.0.50+), Groq SDK, SQLAlchemy (ORM), uv (package manager)
- Database: SQLite (file-based, no setup needed)
- Frontend: React 18 + TypeScript, Vite, Bun (package manager)
- LLM: Qwen 3.6 27B (Groq free tier, no auth required)

### Key Files
- `backend/main.py` — FastAPI routes, streaming generator, thread endpoints
- `backend/db.py` — SQLAlchemy models (Thread, Message), DB initialization
- `backend/agent.py` — LangGraph StateGraph, tools, agent logic
- `frontend/src/App.tsx` — Chat UI, thread dropdown, message history loading
- `docs/LEARNING.md` — Full build log with why/how for each step

## How It Works: Streaming

**Flow:**
1. Frontend `POST /chat/stream` → Backend receives message
2. Backend creates async generator, yields SSE events
3. LangGraph `agent.astream()` produces chunks:
   - `messages` mode: LLM tokens as they generate
   - `updates` mode: node execution state changes
4. Backend filters/batches, sends as `data: JSON\n\n`
5. Frontend reads stream, decodes, parses JSON per event
6. Tokens accumulate in state, UI updates per token
7. Stream closes when agent completes

**Why this matters:**
- User sees output building in real-time (responsive UX)
- No wait for full LLM completion
- Tool execution results stream too (calculator, weather)
- No blocking I/O at any layer

## Testing Verified
- Simple responses (jokes, greetings) ✓
- Calculator tool with streaming ✓
- Weather API tool with streaming ✓
- Complex reasoning (multi-step math) ✓
- Full agent loop (reason → tool → stream result → loop) ✓
- Multiple threads created independently ✓
- Message persistence across requests ✓
- Thread switching + history loading ✓
- Streaming + memory combined (no regression) ✓

## Permission Configuration

Allowlist in `.claude/settings.json` for reduced prompts:
```json
"permissions": {
  "mode": "auto",
  "allow": [
    "Bash(curl -s *)",
    "Bash(lsof -ti:*)",
    "Bash(find *)",
    "Bash(gh repo *)",
    "mcp__docs-langchain__search_docs_by_lang_chain"
  ]
}
```

Note: Global feature flag `tengu_quill_harbor` at account level forces "Accept Edits" mode—project-level `mode: "auto"` doesn't override.

## Next Steps
- RAG (vector storage + semantic search for context window expansion)
- Langfuse tracing (observability + debugging)
- Thread naming/renaming (better UX than auto-generated "New conversation")
- Message search within threads
- React Native app (mobile, after web is stable)

## Dev Commands

**Backend:**
```bash
cd backend && uv run uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend && bun run dev --port 5173
```

**Test streaming (curl):**
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"2+2"}'
```

## Key Decisions

1. **Streaming first**: v2 format unified across modes, SSE for simplicity (no WebSocket overhead)
2. **Groq, not Anthropic**: Free tier (no API key cost), fast inference, same patterns apply to any LLM
3. **React (not React Native) first**: Faster path to working web UI before mobile
4. **Minimal edits**: Streaming + memory added without breaking old endpoints—backward compatible
5. **SQLite for memory**: Simple, file-based, no external DB setup, sufficient for single-machine dev/demo
6. **Thread-based, not session-based**: Users can manage multiple independent conversations, easier to resume later

## Gotchas & Patterns

### Streaming
- **Chunk ordering**: SSE preserves order; accumulate tokens sequentially in state.
- **Partial reads**: Reader may return incomplete SSE events—loop handles buffering across reads.
- **Blank tokens**: LLM sends empty chunks before content; filter with `if content:`.
- **Tool streaming**: Tool results (e.g., calculator) also stream via `messages` mode token chunks.
- **Node updates**: `updates` mode shows only changed keys per node execution, not full state snapshot.

### Memory
- **Message history**: Loads ALL previous messages from DB per thread (no pagination yet)
- **Context window**: Pass full history to agent; LLM's context window is the only limit
- **Message order**: Persisted in creation order, reconstructed as [HumanMessage, AIMessage, ...] for agent
- **Streaming + memory**: Assistant message accumulated during streaming, persisted AFTER stream ends (ensures full text)

## How to Update This File

This file is the single source of truth for project context. Update when:
- Adding new endpoints or tools
- Changing streaming behavior or architecture
- Adding new dependencies or moving to different LLM
- Starting new major features (memory, RAG, etc.)

Recommended: Before each commit, scan for changes that would affect someone reading this file cold. One-liner bug fixes don't need updates; architectural changes do.
