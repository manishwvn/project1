# project1 — Agentic AI, learned step by step

A from-scratch build of an agentic AI stack (LangGraph, Langfuse, tool
calling, memory, RAG) with a native iOS chat client as the front end.
Backend LLM calls run on Groq's free tier — no paid API required.

See [docs/LEARNING.md](docs/LEARNING.md) for the full build log: what was
built at each step, why, and the bugs hit along the way.

## Structure

```
backend/   FastAPI + Groq — the agent backend
ios/       SwiftUI chat client (Xcode project)
docs/      Build log / learning notes
```

## Backend

```
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Requires a `.env` file at the repo root with `GROQ_API_KEY=...` (gitignored,
not included in this repo). `--host 0.0.0.0` is needed for the iOS app to
reach it over the LAN when running on a physical device, not just the
Simulator.

## iOS app

Open `ios/ChatApp/ChatApp.xcodeproj` in Xcode, select a Simulator or a
connected iPhone as the run target, and run. The backend must already be
running — see above.

If running on a physical device, update the backend URL in
`ios/ChatApp/ChatApp/ContentView.swift` to your Mac's LAN IP (Simulator can
use `localhost` directly; a real device cannot).

## Status

Backend: single `/chat` endpoint, no agent framework yet — plain
request → LLM → response, on purpose (see docs/LEARNING.md Step 1).

iOS: bare-bones chat UI (bubbles, markdown rendering, auto-scroll),
verified working on both Simulator and a physical iPhone.

Next: tool calling, memory, RAG, LangGraph orchestration, Langfuse tracing
— one concept at a time, each demoed through the iOS app.
