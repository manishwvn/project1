# project1 — Agentic AI, learned step by step

A from-scratch build of an agentic AI stack (LangGraph, Langfuse, tool
calling, memory, RAG). Backend LLM calls run on Groq's free tier — no paid
API required.

See [docs/LEARNING.md](docs/LEARNING.md) for the full build log: what was
built at each step, why, and the bugs hit along the way.

## Structure

```
backend/   FastAPI + Groq + LangGraph — the agent backend
frontend/  React + Vite (TypeScript) — chat UI for the agent
docs/      Build log / learning notes
```

## Backend

```
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Requires a `.env` file at the repo root with `GROQ_API_KEY=...` (gitignored,
not included in this repo).

## Frontend

```
cd frontend
bun install
bun dev
```

Opens at `http://localhost:5173`. Talks to the backend at
`http://localhost:8000` by default — override with `VITE_API_URL` in
`frontend/.env.local` if the backend runs on a different port.

## Status

Backend: Two endpoints:
- `/chat` — blocking endpoint returns full response
- `/chat/stream` — streaming endpoint (SSE) with token-by-token LLM output + tool execution tracking

Both backed by a LangGraph agent (`backend/agent.py`) with tool calling (calculator, weather).

Frontend: React + Vite chat UI (`frontend/`) that calls `/chat/stream` and displays tokens as they arrive.

Completed: agent with tool calling, streaming responses (v2 format, `messages` + `updates` modes), weather + calculator tools.

Next: conversation memory, RAG, Langfuse tracing. React Native app planned for later once the web UI and agent are further along.
