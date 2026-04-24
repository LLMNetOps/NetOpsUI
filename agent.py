#!/usr/bin/env python3
"""LangGraph ReAct agent for MikroTik network audit via SSH."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterator

import yaml

WORKDIR = Path(__file__).parent
CONFIG_FILE = WORKDIR / "config.yaml"
OLLAMA_BASE_URL = "http://10.45.185.253:11434"
OLLAMA_MODEL = "qwen3.6:35b-a3b-q8_0"

# ── Dependency guard ─────────────────────────────────────────────────────────
_HAS_LANGGRAPH = False
_IMPORT_ERROR = ""
try:
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.errors import GraphRecursionError
    _HAS_LANGGRAPH = True
except ImportError as _e:
    _IMPORT_ERROR = str(_e)

# ── SSH imports from sibling module ─────────────────────────────────────────
try:
    from mikrotik_agent import (
        ssh_run_command,
        ssh_get_dhcp_leases,
        parse_mikrotik_dhcp_output,
    )
    _HAS_SSH = True
except ImportError:
    _HAS_SSH = False
    def ssh_run_command(*a, **kw): return (False, "", "mikrotik_agent not found")
    def ssh_get_dhcp_leases(*a, **kw): return (False, "", "mikrotik_agent not found")
    def parse_mikrotik_dhcp_output(*a, **kw): return []


# ── Config loading ───────────────────────────────────────────────────────────
_SSH_CONFIG: dict[str, Any] = {}
_ROUTERS: list[dict[str, Any]] = []
VALID_ROUTER_NAMES: frozenset[str] = frozenset()
_NAME_TO_ENTRIES: dict[str, list[dict[str, Any]]] = {}


def _load_config() -> None:
    global _SSH_CONFIG, _ROUTERS, VALID_ROUTER_NAMES, _NAME_TO_ENTRIES
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        _SSH_CONFIG = {
            "username": cfg["ssh"]["username"],
            "password": cfg["ssh"]["password"],
            "timeout": int(cfg["ssh"].get("timeout", 15)),
            "port": int(cfg["ssh"].get("port", 22)),
        }
        flat: list[dict[str, Any]] = []
        for r in cfg.get("routers", []):
            for srv in r.get("dhcp_servers", []):
                flat.append({
                    "name": r["name"],
                    "host": r["host"],
                    "ros_version": int(r.get("ros_version", 7)),
                    "dhcp_server": srv,
                })
        _ROUTERS = flat
        _NAME_TO_ENTRIES = {}
        for entry in flat:
            _NAME_TO_ENTRIES.setdefault(entry["name"], []).append(entry)
        VALID_ROUTER_NAMES = frozenset(_NAME_TO_ENTRIES.keys())
    except Exception as exc:
        print(f"[agent] Config load error: {exc}", file=sys.stderr)


_load_config()


def _validate_router(name: str) -> None:
    if name not in VALID_ROUTER_NAMES:
        valid = ", ".join(sorted(VALID_ROUTER_NAMES))
        raise ValueError(f"Router '{name}' tidak dikenal. Pilihan valid: {valid}")


def _ssh_creds() -> dict[str, Any]:
    return {
        "username": _SSH_CONFIG.get("username", ""),
        "password": _SSH_CONFIG.get("password", ""),
        "port": _SSH_CONFIG.get("port", 22),
        "timeout": _SSH_CONFIG.get("timeout", 15),
    }


def _query_leases(entry: dict[str, Any]) -> dict[str, Any]:
    """SSH to one router entry and return parsed stats. Internal helper."""
    creds = _ssh_creds()
    ok, raw, err = ssh_get_dhcp_leases(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        dhcp_server=entry["dhcp_server"],
        port=creds["port"],
        timeout=creds["timeout"],
        ros_version=entry["ros_version"],
    )
    if not ok:
        return {**entry, "ok": False, "error": err, "leases": []}
    leases = parse_mikrotik_dhcp_output(raw)
    bound = sum(1 for l in leases if l.is_active)
    waiting = sum(1 for l in leases if l.is_inactive)
    disabled = sum(1 for l in leases if l.disabled)
    utbk = sum(1 for l in leases if l.is_active and l.hostname == "utbk-os")
    return {
        **entry,
        "ok": True,
        "leases": leases,
        "bound": bound,
        "waiting": waiting,
        "disabled": disabled,
        "utbk": utbk,
        "total": len(leases),
    }


# ── Tools ────────────────────────────────────────────────────────────────────

if _HAS_LANGGRAPH:

    @tool
    def list_routers() -> str:
        """
        Daftar semua router/switch yang tersedia beserta DHCP server-nya.
        Gunakan ini untuk mengetahui nama router yang valid sebelum memanggil tool lain.
        Tidak memerlukan argumen.
        """
        lines = ["Router yang tersedia:\n"]
        seen: dict[str, list[str]] = {}
        for e in _ROUTERS:
            seen.setdefault(e["name"], []).append(e["dhcp_server"])
        for name in sorted(seen):
            entries = _NAME_TO_ENTRIES[name]
            host = entries[0]["host"]
            ros = entries[0]["ros_version"]
            servers = ", ".join(seen[name])
            lines.append(f"  {name:<14} {host:<16} ROS v{ros}  servers: {servers}")
        return "\n".join(lines)

    @tool
    def check_reachability(router_name: str) -> str:
        """
        Cek apakah router dapat dijangkau via ping.
        Args:
            router_name: Nama router (contoh: DTI, FIB, FILKOM). Gunakan list_routers() untuk daftar valid.
        """
        _validate_router(router_name)
        hosts = list({e["host"] for e in _NAME_TO_ENTRIES[router_name]})
        results = []
        for host in hosts:
            try:
                res = subprocess.run(
                    ["ping", "-c", "1", "-W", "3", host],
                    capture_output=True, text=True, timeout=5,
                )
                reachable = res.returncode == 0
                # Parse RTT from ping output
                rtt = "-"
                m = re.search(r"time=([\d.]+)", res.stdout)
                if m:
                    rtt = f"{m.group(1)} ms"
                results.append(f"{host}: {'✓ reachable' if reachable else '✗ unreachable'} (RTT: {rtt})")
            except Exception as e:
                results.append(f"{host}: error — {e}")
        return f"Reachability {router_name}:\n" + "\n".join(results)

    @tool
    def get_system_info(router_name: str) -> str:
        """
        Ambil informasi sistem router: CPU, memori, uptime, versi RouterOS.
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        """
        _validate_router(router_name)
        entry = _NAME_TO_ENTRIES[router_name][0]
        creds = _ssh_creds()
        cmd = "/system/resource/print" if entry["ros_version"] == 7 else "system resource print"
        ok, out, err = ssh_run_command(
            host=entry["host"],
            username=creds["username"],
            password=creds["password"],
            command=cmd,
            port=creds["port"],
            timeout=creds["timeout"],
        )
        if not ok:
            return f"Gagal terhubung ke {router_name} ({entry['host']}): {err}"
        return f"System info {router_name} ({entry['host']}):\n{out.strip()}"

    @tool
    def get_dhcp_leases(router_name: str, dhcp_server: str) -> str:
        """
        Ambil data DHCP lease live dari satu DHCP server tertentu di router.
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
            dhcp_server: Nama DHCP server (contoh: dhcp-lab-tik). Gunakan list_routers() untuk daftar valid.
        """
        _validate_router(router_name)
        # Validate dhcp_server is in the allowed list for this router
        valid_servers = [e["dhcp_server"] for e in _NAME_TO_ENTRIES[router_name]]
        if dhcp_server not in valid_servers:
            return (
                f"DHCP server '{dhcp_server}' tidak ditemukan di {router_name}. "
                f"Server yang valid: {', '.join(valid_servers)}"
            )
        entry = next(
            e for e in _NAME_TO_ENTRIES[router_name] if e["dhcp_server"] == dhcp_server
        )
        result = _query_leases(entry)
        if not result["ok"]:
            return f"Gagal ambil lease dari {router_name}/{dhcp_server}: {result['error']}"
        leases = result["leases"]
        lines = [
            f"DHCP Lease — {router_name} / {dhcp_server} ({entry['host']})",
            f"Total: {result['total']}  bound: {result['bound']}  "
            f"waiting: {result['waiting']}  disabled: {result['disabled']}  "
            f"utbk-os: {result['utbk']}",
            "",
        ]
        # Show up to 30 leases
        for l in leases[:30]:
            status = "bound" if l.is_active else ("waiting" if l.is_inactive else "disabled")
            lines.append(
                f"  {l.ip_address:<16} {l.mac_address}  {l.hostname or '-':<20} {status}"
            )
        if len(leases) > 30:
            lines.append(f"  ... ({len(leases) - 30} lease lagi tidak ditampilkan)")
        return "\n".join(lines)

    @tool
    def get_all_leases_for_router(router_name: str) -> str:
        """
        Ambil dan agregasi semua DHCP lease dari semua DHCP server di satu router.
        Berguna untuk router seperti FILKOM (5 server) atau FK-8 (3 server).
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        """
        _validate_router(router_name)
        entries = _NAME_TO_ENTRIES[router_name]
        lines = [f"Semua DHCP server di {router_name}:"]
        total_bound = total_waiting = total_disabled = total_utbk = 0
        for entry in entries:
            result = _query_leases(entry)
            if not result["ok"]:
                lines.append(f"  {entry['dhcp_server']}: GAGAL — {result['error']}")
            else:
                lines.append(
                    f"  {entry['dhcp_server']}: "
                    f"bound={result['bound']} waiting={result['waiting']} "
                    f"disabled={result['disabled']} utbk={result['utbk']}"
                )
                total_bound += result["bound"]
                total_waiting += result["waiting"]
                total_disabled += result["disabled"]
                total_utbk += result["utbk"]
        lines.append("")
        lines.append(
            f"TOTAL: bound={total_bound} waiting={total_waiting} "
            f"disabled={total_disabled} utbk={total_utbk}"
        )
        return "\n".join(lines)

    @tool
    def audit_all_routers() -> str:
        """
        Audit menyeluruh semua router: ambil data DHCP lease dari seluruh perangkat secara paralel.
        Menampilkan ringkasan status per router. Proses ini membutuhkan 30-90 detik.
        Tidak memerlukan argumen.
        """
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_query_leases, entry): entry for entry in _ROUTERS}
            for future in as_completed(futures, timeout=120):
                try:
                    results.append(future.result())
                except Exception as e:
                    entry = futures[future]
                    results.append({**entry, "ok": False, "error": str(e)})

        # Aggregate per router name + server
        lines = [
            f"{'Router':<14} {'Server':<22} {'Host':<16} {'Bound':>6} {'Wait':>6} {'Dis':>5} {'UTBK':>6} Status",
            "-" * 90,
        ]
        total_b = total_w = total_d = total_u = ok_count = fail_count = 0
        for r in sorted(results, key=lambda x: (x["name"], x["dhcp_server"])):
            if r["ok"]:
                lines.append(
                    f"  {r['name']:<14} {r['dhcp_server']:<22} {r['host']:<16} "
                    f"{r['bound']:>6} {r['waiting']:>6} {r['disabled']:>5} {r['utbk']:>6}  ✓"
                )
                total_b += r["bound"]
                total_w += r["waiting"]
                total_d += r["disabled"]
                total_u += r["utbk"]
                ok_count += 1
            else:
                lines.append(
                    f"  {r['name']:<14} {r['dhcp_server']:<22} {r['host']:<16} "
                    f"{'':>6} {'':>6} {'':>5} {'':>6}  ✗ {r.get('error','')[:30]}"
                )
                fail_count += 1
        lines.append("-" * 90)
        lines.append(
            f"  {'TOTAL':<14} {ok_count} OK / {fail_count} GAGAL"
            f"{'':>16} {total_b:>6} {total_w:>6} {total_d:>5} {total_u:>6}"
        )
        return "\n".join(lines)

    @tool
    def search_device(query: str) -> str:
        """
        Cari perangkat berdasarkan IP address atau MAC address di semua router.
        Args:
            query: IP address (contoh: 10.39.0.101) atau MAC address (contoh: dc:a6:32:1b:2c:3d)
                   atau sebagian MAC (contoh: dc:a6).
        """
        # Security: reject shell metacharacters
        if re.search(r'[|;&$`\\"\']', query):
            return "Error: karakter tidak valid dalam query."
        query = query.strip()
        if not query:
            return "Error: query kosong."
        q = query.lower()

        matches: list[str] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_query_leases, entry): entry for entry in _ROUTERS}
            for future in as_completed(futures, timeout=120):
                try:
                    result = future.result()
                    if not result["ok"]:
                        continue
                    for l in result["leases"]:
                        ip_match = q in l.ip_address.lower()
                        mac_match = q in l.mac_address.lower().replace("-", ":")
                        if ip_match or mac_match:
                            status = "bound" if l.is_active else ("waiting" if l.is_inactive else "disabled")
                            matches.append(
                                f"  {result['name']}/{result['dhcp_server']}  "
                                f"{l.ip_address:<16} {l.mac_address}  "
                                f"{l.hostname or '-':<20} {status}"
                            )
                except Exception:
                    pass

        if not matches:
            return f"Perangkat '{query}' tidak ditemukan di router mana pun."
        header = f"Hasil pencarian '{query}' ({len(matches)} ditemukan):"
        return header + "\n" + "\n".join(matches)

    _TOOLS = [
        list_routers,
        check_reachability,
        get_system_info,
        get_dhcp_leases,
        get_all_leases_for_router,
        audit_all_routers,
        search_device,
    ]

    _SYSTEM_PROMPT = (
        "Kamu adalah network engineer AI yang dapat melakukan monitoring dan audit "
        "jaringan DHCP pada perangkat MikroTik untuk ujian UTBK 2026. "
        "Kamu memiliki akses SSH ke semua router melalui tools yang tersedia. "
        "Kredensial SSH ditangani secara internal — jangan pernah meminta password kepada pengguna. "
        "Jika tidak yakin nama router yang valid, panggil list_routers() terlebih dahulu. "
        "Gunakan tools untuk mendapatkan data live saat ditanya tentang kondisi terkini. "
        "Jawab dalam Bahasa Indonesia. "
        "Gunakan istilah teknis jaringan dalam bahasa Inggris dengan backtick: "
        "`bound`, `waiting`, `lease`, `DHCP`, `IP`, `MAC`, `router`, `subnet`. "
        "Jawaban ringkas dan langsung ke poin kecuali diminta detail."
    )

else:
    _TOOLS = []
    _SYSTEM_PROMPT = ""


# ── Agent factory ─────────────────────────────────────────────────────────────

def create_agent(thread_id: str) -> tuple[Any, dict[str, Any]]:
    """Create a LangGraph ReAct agent with MemorySaver. Returns (agent, config)."""
    if not _HAS_LANGGRAPH:
        raise RuntimeError(f"LangGraph tidak tersedia: {_IMPORT_ERROR}")

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.4,
        num_predict=1024,
    )
    memory = MemorySaver()
    agent = create_react_agent(
        llm,
        tools=_TOOLS,
        checkpointer=memory,
        prompt=_SYSTEM_PROMPT,
    )
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 15,
    }
    return agent, config


def stream_agent_response(
    agent: Any,
    config: dict[str, Any],
    user_message: str,
) -> Iterator[tuple[str, str]]:
    """
    Stream agent events. Yields (event_type, content) tuples:
      "tool_call"   → tool is being invoked
      "tool_result" → tool returned a result
      "ai"          → final AI text response
    """
    _think_re = re.compile(r"<think>.*?</think>", re.DOTALL)

    for chunk in agent.stream(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
        stream_mode="updates",
    ):
        for node_name, node_output in chunk.items():
            messages = node_output.get("messages", [])
            for msg in messages:
                # Tool calls requested by the agent
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        args_str = ", ".join(
                            f"{k}={json.dumps(v)}" for k, v in tc.get("args", {}).items()
                        )
                        yield "tool_call", f"{tc['name']}({args_str})"

                # Tool results returned to the agent
                elif isinstance(msg, ToolMessage):
                    # Summarise: first 120 chars of content
                    summary = msg.content[:120].replace("\n", " ")
                    if len(msg.content) > 120:
                        summary += "…"
                    yield "tool_result", summary

                # Final AI text
                elif hasattr(msg, "content") and msg.content:
                    content = _think_re.sub("", msg.content).strip()
                    if content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
                        yield "ai", content
