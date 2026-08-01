# project1

FastAPI backend + Vite/React frontend, LangChain/LangGraph agent code.

## Dev commands

Backend:
```
cd backend && uv run uvicorn main:app --reload --port 8000
```

Frontend:
```
cd frontend && bun run dev --port 5173
```

## MCP servers (this project)

- `docs-langchain` — LangChain/LangGraph documentation search
- `reference-langchain` — LangChain/LangGraph API reference

Tools exposed when enabled:
```
docs-langchain_search_docs_by_lang_chain
docs-langchain_query_docs_filesystem_docs_by_lang_chain
docs-langchain_submit_feedback
reference-langchain_search_api
reference-langchain_get_symbol
```

## Structure

- `backend/` — agent.py, langchain_basics.py, langgraph_agent.py, main.py (uv-managed)
- `frontend/` — Vite + React + TS (bun-managed)
- `reference_docs/`, `docs/`, `scripts/`
