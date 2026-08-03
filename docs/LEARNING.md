# Learning Log — Agentic AI Step by Step

Goal: learn LangGraph, Langfuse, tool calls, memory, RAG — step by step.
Backend LLM calls use Groq (free tier) and later OpenRouter, not Anthropic
API (no budget for that). Claude Code is the dev tool writing all code.

## Step 1 — Bare backend, no agent logic yet

**What:** `backend/` — a uv-managed Python 3.12 project with FastAPI +
Groq SDK. One endpoint: `POST /chat` — takes `{"message": "..."}`, sends it
straight to Groq's `qwen/qwen3-32b` model, returns `{"reply": "..."}`.
Qwen3 is a reasoning model — Groq's `reasoning_format="hidden"` param
suppresses the `<think>...</think>` block so only the final answer comes
back.

**Why this first:** no agent framework yet on purpose. Before LangGraph adds
orchestration, want plain request -> LLM -> response working, so later when
LangGraph is introduced it's clear what it's adding (graph state, multi-step
reasoning, tool routing) rather than mixing that with "does the API call even
work."

**Why uv:** fast, single tool for venv + dependency + Python version pinning.
Avoids juggling pip/venv/pyenv separately.

**Why FastAPI:** minimal boilerplate, async-friendly, matters once
tool-calling / streaming responses come in later steps.

**Files:**
- `backend/main.py` — the FastAPI app + `/chat` route
- `backend/pyproject.toml` — deps: fastapi, uvicorn, groq, python-dotenv
- `.env` (repo root, gitignored) — holds `GROQ_API_KEY`

**How to run:**
```
cd backend
uv run uvicorn main:app --port 8000 --reload
```
Test:
```
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"say hi in 3 words"}'
```

**Verified:** server boots, `/chat` returns a real Groq completion.

## Step 2 — LangGraph agent with tool calling

**What:** `backend/agent.py` — a LangGraph `StateGraph` agent replacing the
plain Groq call in `/chat`. State is a `TypedDict` accumulating messages
(`operator.add`). Two tools bound to the LLM: `calculator` (evaluates math
expressions) and `get_weather` (OpenWeatherMap lookup). Graph: `chat` node
calls the LLM, `tools` node executes any `tool_calls` it returns, a
conditional edge (`should_continue`) loops back to `chat` if more tool calls
are pending or ends otherwise.

**Why:** learn the core agent loop (LLM decision -> tool execution -> result
fed back -> LLM decision again) before adding memory, RAG, or Langfuse
tracing on top.

**Files:**
- `backend/agent.py` — `AgentState`, tool definitions, `create_agent()`
- `backend/main.py` — imports `create_agent()`, wraps incoming message in
  `HumanMessage`, invokes the compiled graph, extracts the last message's
  content as the reply
- `backend/pyproject.toml` — added `langgraph` dependency

**Verified:** `/chat` with `"2 + 2"` and `"10 * 5"` routes through the
calculator tool; `"Tell me a joke"` returns a direct LLM response with no
tool call.

## Step 3 — React frontend (web chat UI)

**What:** `frontend/` — a Vite + React + TypeScript app, package-managed and
run with bun. Single `App.tsx` chat screen: text input, send button, message
list rendered as bubbles (user right-aligned, agent left-aligned), calls
`POST {VITE_API_URL}/chat` and appends the reply. `VITE_API_URL` defaults to
`http://localhost:8000`, overridable via `frontend/.env.local`.

**Why React (not React Native) first:** the near-term goal is a web-based
way to interact with the agent. React Native matters once a real mobile app
is wanted again, but that's a separate, later step — plain React + Vite is
the fastest path to a working browser UI now.

**Why bun:** single fast tool for install + dev server, avoids
npm/node_modules slowness for a small frontend.

**Backend change:** added `CORSMiddleware` in `backend/main.py` allowing
`http://localhost:5173` so the Vite dev server can call `/chat` directly.

**Files:**
- `frontend/src/App.tsx` — chat UI + fetch call to backend
- `frontend/src/App.css` — chat layout/styling
- `frontend/.env.local` (gitignored) — `VITE_API_URL` override
- `backend/main.py` — CORS middleware added

**Verified:** `bun install` + `bun dev`, sent "2 + 2" through the UI, agent
replied "Result: 4" via the calculator tool — full browser -> FastAPI ->
LangGraph agent round trip confirmed working.

## Step 4 — Streaming responses (token-by-token)

**What:** `/chat/stream` endpoint (SSE) using `agent.astream()` with `version="v2"` and `stream_mode=["messages", "updates"]`.

Backend streams two event types:
- `token` events with LLM output chunks (one per generated token)
- `progress` events with node execution updates (agent steps)

Frontend reads the response stream using `ReadableStream` + `TextDecoder`, accumulates tokens, updates UI in real-time as each token arrives.

**Why:** UX improvement — user sees output building token-by-token instead of waiting for full response. More responsive feel, better perceived performance.

**Implementation:**
- Backend (`backend/main.py`): Added `/chat/stream` endpoint with async generator yielding SSE events
- Frontend (`frontend/src/App.tsx`): Modified `sendMessage()` to consume SSE stream with `res.body.getReader()` instead of `res.json()`

**How it works:**
1. LLM generates tokens sequentially
2. Each token packaged as SSE event: `data: {"type": "token", "content": "token_text"}\n\n`
3. Frontend reads bytes from stream, decodes, parses JSON per event
4. Accumulates tokens in state, updates message bubble on each token
5. Tool execution (calculator, weather) also streams results
6. Stream closes when agent completes

**Verified:** `/chat/stream` tested with:
- Simple responses (joke)
- Calculator tool calls (42 * 17 = 714)
- Weather API calls (SF weather data)
- Complex reasoning (apple math breakdown)

Original `/chat` endpoint preserved for backward compatibility.

## Next steps (not started)
- Conversation memory
- RAG
- Langfuse tracing
- React Native app (once web UI + agent are further along)
