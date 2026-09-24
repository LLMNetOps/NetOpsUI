"""Server-side chat runs for NetOps Agent.

NetOps Agent's POST /chat is stateless and streams SSE for as long as the run
lasts. When the browser called it directly, a page refresh cut the stream and
the answer was never saved. Here the manager makes the call instead: it
records the user message, reads the agent's stream in a background thread,
keeps the events in memory for (re)attaching viewers and stores the final
answer in the database whether or not any browser is still watching.

Runs live in this process's memory only (one uvicorn worker). If the manager
restarts mid-run the run is lost; init_runs() clears the stale "running" flags.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from collections.abc import Iterator

import db

AGENT_URL = os.environ.get("NETOPS_AGENT_URL", "http://127.0.0.1:8100").rstrip("/")
READ_TIMEOUT_S = 3600      # delegations have been traced at 250-1600+ s with no bytes on the wire
KEEP_DONE_S = 600          # finished runs stay attachable for a while (replay after a quick finish)
PING_S = 15                # keeps proxies from closing an idle event stream


class Run:
    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id
        self.events: list[dict] = []
        self.cond = threading.Condition()
        self.done = False
        self.cancelled = False
        self.finished_at = 0.0
        self.resp = None

    def emit(self, ev: dict) -> None:
        with self.cond:
            self.events.append(ev)
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.done = True
            self.finished_at = time.time()
            self.cond.notify_all()


_runs: dict[str, Run] = {}
_lock = threading.Lock()


def init_runs() -> None:
    with db.conn() as c:
        c.execute("UPDATE chat_threads SET running_since=NULL WHERE running_since IS NOT NULL")


def _save_agent_message(thread_id: str, content: str) -> None:
    with db.conn() as c:
        c.execute("INSERT INTO chat_messages (thread_id, role, content) "
                  "SELECT ?, 'agent', ? WHERE EXISTS (SELECT 1 FROM chat_threads WHERE id=?)",
                  (thread_id, content, thread_id))
        c.execute("UPDATE chat_threads SET running_since=NULL, "
                  "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (thread_id,))


def is_active(thread_id: str) -> bool:
    r = _runs.get(thread_id)
    return bool(r and not r.done)


def start(thread_id: str, messages: list[dict]) -> None:
    """Begin a run. `messages` is the full conversation ending with the new user
    message. Raises RuntimeError if this thread already has a run in progress."""
    with _lock:
        if is_active(thread_id):
            raise RuntimeError("thread sedang diproses")
        now = time.time()
        for tid in [t for t, r in _runs.items() if r.done and now - r.finished_at > KEEP_DONE_S]:
            del _runs[tid]
        run = Run(thread_id)
        _runs[thread_id] = run
    threading.Thread(target=_worker, args=(run, messages), daemon=True).start()


def _worker(run: Run, messages: list[dict]) -> None:
    answer = ""
    failure = ""
    try:
        req = urllib.request.Request(
            AGENT_URL + "/chat", json.dumps({"messages": messages}).encode(),
            {"Content-Type": "application/json", "Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=READ_TIMEOUT_S) as resp:
            run.resp = resp
            for raw in resp:
                if run.cancelled:
                    break
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:].strip())
                except ValueError:
                    continue
                kind = data.get("type")
                if kind == "delta":
                    answer += data.get("content") or ""
                    run.emit({"type": "delta", "text": data.get("content") or ""})
                elif kind == "tool_call":
                    run.emit({"type": "tool_end", "name": data.get("name"),
                              "detail": data.get("arguments") or "",
                              "durationMs": (data.get("duration") or 0) * 1000})
                elif kind == "done":
                    break
    except Exception as e:  # noqa: BLE001 — anything from the agent connection ends the run
        if not run.cancelled:
            failure = f"Gagal menghubungi NetOps Agent: {e}"
    try:
        if run.cancelled:
            run.emit({"type": "stopped", "text": "Dihentikan operator. Proses di server NetOps Agent tetap berjalan sampai selesai, tetapi hasilnya tidak diterima."})
        elif failure:
            run.emit({"type": "error", "text": failure})
            if not answer:
                answer = f"**Error:** {failure}"
        _save_agent_message(run.thread_id, answer)
    except Exception:  # noqa: BLE001 — e.g. the thread was deleted mid-run
        pass
    finally:
        run.emit({"type": "done"})
        run.finish()


def cancel(thread_id: str) -> bool:
    run = _runs.get(thread_id)
    if not run or run.done:
        return False
    run.cancelled = True
    try:
        if run.resp is not None:
            run.resp.close()
    except Exception:  # noqa: BLE001
        pass
    return True


def stream(thread_id: str, after: int = 0) -> Iterator[str]:
    """SSE frames for the thread's run, from event index `after`. Ends after the
    run's final 'done' event; with no run it ends at once."""
    run = _runs.get(thread_id)
    if run is None:
        yield 'data: {"type": "done"}\n\n'
        return
    idx = max(0, after)
    while True:
        with run.cond:
            if idx >= len(run.events) and not run.done:
                run.cond.wait(PING_S)
            batch = run.events[idx:]
            finished = run.done and idx + len(batch) >= len(run.events)
        if batch:
            idx += len(batch)
            for ev in batch:
                yield f"data: {json.dumps(ev)}\n\n"
        elif not finished:
            yield ": ping\n\n"
        if finished:
            return
