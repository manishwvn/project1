import os
import json
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session

from agent import create_agent
from db import init_db, get_db, Thread, Message

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://manishwvn.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = create_agent()

init_db()


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    thread_id: str


class ThreadInfo(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageInfo(BaseModel):
    role: str
    content: str
    created_at: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    thread_id = request.thread_id or str(uuid.uuid4())

    db_thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not db_thread:
        db_thread = Thread(id=thread_id, title="New conversation")
        db.add(db_thread)
        db.commit()

    db.add(Message(thread_id=thread_id, role="user", content=request.message))
    db.commit()

    messages_from_db = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at).all()

    langchain_messages = []
    for msg in messages_from_db:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))

    initial_state = {"messages": langchain_messages}
    result = agent.invoke(initial_state)

    last_message = result["messages"][-1]
    reply = last_message.content if hasattr(last_message, 'content') else str(last_message)

    db.add(Message(thread_id=thread_id, role="assistant", content=reply))
    db.commit()

    return ChatResponse(reply=reply, thread_id=thread_id)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    thread_id = request.thread_id or str(uuid.uuid4())

    db_thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not db_thread:
        db_thread = Thread(id=thread_id, title="New conversation")
        db.add(db_thread)
        db.commit()

    db.add(Message(thread_id=thread_id, role="user", content=request.message))
    db.commit()

    messages_from_db = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at).all()

    langchain_messages = []
    for msg in messages_from_db:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))

    async def event_generator():
        assistant_reply = ""
        initial_state = {"messages": langchain_messages}
        async for chunk in agent.astream(
            initial_state,
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            if chunk["type"] == "messages":
                msg, metadata = chunk["data"]
                content = getattr(msg, 'content', '') or ''
                if content:
                    assistant_reply += content
                    event_data = {"type": "token", "content": content}
                    yield f"data: {json.dumps(event_data)}\n\n"
            elif chunk["type"] == "updates":
                for node_name, node_state in chunk["data"].items():
                    event_data = {"type": "progress", "node": node_name, "state": str(node_state)}
                    yield f"data: {json.dumps(event_data)}\n\n"

        db.add(Message(thread_id=thread_id, role="assistant", content=assistant_reply))
        db.commit()

        event_data = {"type": "thread_id", "thread_id": thread_id}
        yield f"data: {json.dumps(event_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/threads", response_model=list[ThreadInfo])
def list_threads(db: Session = Depends(get_db)):
    threads = db.query(Thread).order_by(Thread.updated_at.desc()).all()
    return [
        ThreadInfo(
            id=t.id,
            title=t.title,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in threads
    ]


@app.get("/threads/{thread_id}", response_model=list[MessageInfo])
def get_thread_messages(thread_id: str, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at).all()
    return [
        MessageInfo(
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@app.post("/threads", response_model=ThreadInfo)
def create_thread(db: Session = Depends(get_db)):
    thread_id = str(uuid.uuid4())
    thread = Thread(id=thread_id, title="New conversation")
    db.add(thread)
    db.commit()
    return ThreadInfo(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )


@app.delete("/threads/{thread_id}")
def delete_thread(thread_id: str, db: Session = Depends(get_db)):
    db.query(Message).filter(Message.thread_id == thread_id).delete()
    db.query(Thread).filter(Thread.id == thread_id).delete()
    db.commit()
    return {"success": True}
