#!/usr/bin/env python3
"""NetOps AI — Web Server.

Exposes agent.py public API over HTTP for the web frontend.

Run:
    python server.py
    # or: uvicorn server:app --reload
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"

import agent as _agent

app = FastAPI(title="NetOps AI", docs_url=None, redoc_url=None)

# ── Session store ─────────────────────────────────────────────────────────────
_sessions: dict[str, tuple[Any, Any]] = {}


def _get_or_create_session(thread_id: str) -> tuple[Any, Any]:
    if thread_id not in _sessions:
        log.info("New session: %s", thread_id)
        graph, config = _agent.create_agent(thread_id=thread_id)
        _sessions[thread_id] = (graph, config)
    return _sessions[thread_id]


# ── Async streaming helper ────────────────────────────────────────────────────

async def _stream_events(gen: Iterator[tuple[str, str]]) -> AsyncGenerator[str, None]:
    """Wrap sync generator → async SSE lines.

    Runs the blocking generator in a thread pool and forwards events via an
    asyncio.Queue using call_soon_threadsafe so the queue is only touched from
    the event-loop thread.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    def _produce() -> None:
        try:
            for event_type, content in gen:
                loop.call_soon_threadsafe(queue.put_nowait, (event_type, content))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    future = loop.run_in_executor(None, _produce)
    while True:
        item = await queue.get()
        if item is None:
            break
        event_type, content = item
        payload = json.dumps({"type": event_type, "content": content})
        yield f"data: {payload}\n\n"
    await future


# ── Request models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ApproveRequest(BaseModel):
    thread_id: str
    decision: str  # "approved" | "rejected"


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    graph, config = _get_or_create_session(req.thread_id)
    gen = _agent.stream_agent_response(graph, config, req.message)
    return StreamingResponse(
        _stream_events(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/approve")
async def approve(req: ApproveRequest) -> StreamingResponse:
    if req.thread_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    graph, config = _sessions[req.thread_id]
    gen = _agent.resume_after_approval(graph, config, req.decision)
    return StreamingResponse(
        _stream_events(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/metrics")
def metrics(n: int = 100) -> list[dict]:
    return _agent.get_token_metrics(n)


@app.post("/session/new")
def new_session() -> dict:
    thread_id = str(uuid.uuid4())
    _get_or_create_session(thread_id)
    return {"thread_id": thread_id}


# ── Static files ──────────────────────────────────────────────────────────────

app.mount("/fonts", StaticFiles(directory=FRONTEND_DIR / "fonts"), name="fonts")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
