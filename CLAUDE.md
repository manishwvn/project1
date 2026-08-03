# project1 — Agentic AI Chat with Streaming

Fast-learning build of an agentic AI stack with real-time streaming responses. Backend: FastAPI + LangGraph + Groq. Frontend: React + Vite.

## Current State

### Completed
- LangGraph agent with tool calling (calculator, weather API)
- Streaming endpoint (`/chat/stream`) with SSE + Server-Sent Events
- Frontend real-time token display (token-by-token accumulation)
- Backward-compatible blocking endpoint (`/chat`)
- Full agent loop: reasoning → tool calls → tool execution → streaming results

### Architecture

**Backend** (`backend/main.py`):
- Two endpoints:
  - `POST /chat` — blocking, returns `{"reply": "..."}` (original, unchanged)
  - `POST /chat/stream` — SSE, streams `data: {"type": "token"|"progress", ...}\n\n` events
- Uses `agent.astream()` with `stream_mode=["messages", "updates"]` and `version="v2"`
- Filters empty tokens, batches progress events

**Frontend** (`frontend/src/App.tsx`):
- `sendMessage()` fetches `/chat/stream`, reads response body with `getReader()`
- Accumulates tokens in state, updates message bubble per token
- No UI changes—same styling, just streaming instead of blocking

**Agent** (`backend/agent.py`):
- StateGraph with nodes: `chat` (LLM), `tools` (tool execution)
- Conditional routing: loop back to chat if tool calls present, else END
- Tools: `calculator` (math), `get_weather` (OpenWeatherMap API)

### Tech Stack
- Backend: FastAPI (uvicorn), LangGraph (v0.0.50+), Groq SDK, uv (package manager)
- Frontend: React 18 + TypeScript, Vite, Bun (package manager)
- LLM: Qwen 3.6 27B (Groq free tier, no auth required)

### Key Files
- `backend/main.py` — FastAPI routes, streaming generator
- `backend/agent.py` — LangGraph StateGraph, tools, agent logic
- `frontend/src/App.tsx` — Chat UI, SSE reader, token accumulation
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
- Conversation memory (thread-based state persistence)
- RAG (vector storage + semantic search for context)
- Langfuse tracing (observability + debugging)
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
4. **Minimal edits**: Streaming added without removing blocking endpoint—backward compatible
5. **No auth/persistence yet**: Focus on agent + streaming working before adding memory layer

## Gotchas & Patterns

- **Chunk ordering**: SSE preserves order; accumulate tokens sequentially in state.
- **Partial reads**: Reader may return incomplete SSE events—loop handles buffering across reads.
- **Blank tokens**: LLM sends empty chunks before content; filter with `if content:`.
- **Tool streaming**: Tool results (e.g., calculator) also stream via `messages` mode token chunks.
- **Node updates**: `updates` mode shows only changed keys per node execution, not full state snapshot.

## How to Update This File

This file is the single source of truth for project context. Update when:
- Adding new endpoints or tools
- Changing streaming behavior or architecture
- Adding new dependencies or moving to different LLM
- Starting new major features (memory, RAG, etc.)

Recommended: Before each commit, scan for changes that would affect someone reading this file cold. One-liner bug fixes don't need updates; architectural changes do.
