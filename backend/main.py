import os
import json

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent import create_agent

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = create_agent()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    initial_state = {"messages": [HumanMessage(content=request.message)]}
    result = agent.invoke(initial_state)

    # Extract final response from messages
    last_message = result["messages"][-1]
    reply = last_message.content if hasattr(last_message, 'content') else str(last_message)

    return ChatResponse(reply=reply)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        initial_state = {"messages": [HumanMessage(content=request.message)]}
        async for chunk in agent.astream(
            initial_state,
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            if chunk["type"] == "messages":
                msg, metadata = chunk["data"]
                # Handle both empty token chunks and actual content
                content = getattr(msg, 'content', '') or ''
                if content:  # Only send non-empty tokens
                    event_data = {"type": "token", "content": content}
                    yield f"data: {json.dumps(event_data)}\n\n"
            elif chunk["type"] == "updates":
                # Track node execution for progress
                for node_name, node_state in chunk["data"].items():
                    event_data = {"type": "progress", "node": node_name, "state": str(node_state)}
                    yield f"data: {json.dumps(event_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
