#!/usr/bin/env python3
"""Load test — kirim sequence query ke agent, ukur latency + event count per query."""

from __future__ import annotations
import sys
import time

sys.path.insert(0, ".")

from agent import create_agent, stream_agent_response  # noqa: E402

QUERIES = [
    ("greeting",       "halo, siapa kamu?"),
    ("morning-check",  "morning check kampus"),
    ("bgp-status",     "cek BGP session GATE-IDREN-UB"),
    ("traffic",        "cek top traffic semua router"),
    ("dhcp-audit",     "audit DHCP pool semua router"),
]

WIDTH = 42


def run() -> None:
    graph, config = create_agent(thread_id="load-test")
    print(f"\n{'Query':<{WIDTH}}  {'Elapsed':>8}  {'Events':>6}  {'Last event'}")
    print("-" * (WIDTH + 32))

    for name, query in QUERIES:
        label = f"[{name}] {query}"[:WIDTH]
        t0 = time.time()
        events: list[tuple[str, str]] = []
        last_type = "—"
        try:
            for ev_type, content in stream_agent_response(graph, config, query):
                events.append((ev_type, content))
                last_type = ev_type
                # print live progress
                marker = {"routing": "→", "tool_call": "⚙", "tool_result": "✓",
                          "ai": "💬", "approval_required": "⚠", "error": "✗"}.get(ev_type, ".")
                print(f"\r  {marker} {ev_type:<18} ({len(events):>3} events)", end="", flush=True)
        except Exception as exc:
            last_type = f"ERROR: {exc}"

        elapsed = time.time() - t0
        print(f"\r{label:<{WIDTH}}  {elapsed:>7.1f}s  {len(events):>6}  {last_type}")

    print()


if __name__ == "__main__":
    run()
