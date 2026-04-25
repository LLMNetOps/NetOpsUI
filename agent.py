#!/usr/bin/env python3
"""LangGraph ReAct agent for MikroTik network audit via SSH."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterator

import yaml

WORKDIR = Path(__file__).parent


def _load_dotenv() -> None:
    """Load .env file into os.environ if present."""
    env_file = WORKDIR / ".env"
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and key not in os.environ:  # don't override existing env vars
                os.environ[key] = val


_load_dotenv()

CONFIG_FILE = WORKDIR / "config.yaml"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6:35b-a3b-q8_0")

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


def _validate_router(name: str) -> str:
    """Validate router name (case-insensitive) and return canonical name."""
    canonical = name.upper()
    if canonical not in VALID_ROUTER_NAMES:
        # Try case-insensitive match for names like FK-1, FT-GBE
        for valid_name in VALID_ROUTER_NAMES:
            if valid_name.upper() == canonical:
                return valid_name
        valid = ", ".join(sorted(VALID_ROUTER_NAMES))
        raise ValueError(f"Router '{name}' tidak dikenal. Pilihan valid: {valid}")
    return canonical


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
        router_name = _validate_router(router_name)
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
        router_name = _validate_router(router_name)
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
        router_name = _validate_router(router_name)
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
        router_name = _validate_router(router_name)
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
    def get_router_log(router_name: str, topic: str = "", lines: int = 30) -> str:
        """
        Baca log sistem dari router MikroTik via SSH.
        Berguna untuk melihat pesan error, DHCP events, dan aktivitas sistem.
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
            topic: Filter topic log (opsional). Contoh: 'dhcp', 'system', 'firewall',
                   'error', 'warning', 'info'. Kosongkan untuk semua log.
            lines: Jumlah baris log yang diambil (default 30, maksimal 100).
        """
        router_name = _validate_router(router_name)
        entry = _NAME_TO_ENTRIES[router_name][0]
        creds = _ssh_creds()

        lines = max(1, min(int(lines), 100))

        # Build MikroTik log command based on ROS version and topic filter
        if entry["ros_version"] == 7:
            base_cmd = "/log/print"
        else:
            base_cmd = "log print"

        if topic.strip():
            # Sanitize topic: only allow alphanumeric and hyphen
            safe_topic = re.sub(r'[^a-zA-Z0-9\-]', '', topic.strip())
            if safe_topic:
                cmd = f'{base_cmd} where topics~"{safe_topic}"'
            else:
                cmd = base_cmd
        else:
            cmd = base_cmd

        ok, out, err = ssh_run_command(
            host=entry["host"],
            username=creds["username"],
            password=creds["password"],
            command=cmd,
            port=creds["port"],
            timeout=creds["timeout"],
        )

        if not ok:
            return f"Gagal ambil log dari {router_name} ({entry['host']}): {err}"

        if not out.strip():
            topic_info = f" (topic: {topic})" if topic.strip() else ""
            return f"Tidak ada log ditemukan di {router_name}{topic_info}."

        # Take last N lines
        log_lines = out.strip().splitlines()
        total = len(log_lines)
        view = log_lines[-lines:]

        header = (
            f"Log {router_name} ({entry['host']})"
            + (f" — topic: {topic}" if topic.strip() else "")
            + f"\nMenunjukkan {len(view)} dari {total} baris:\n"
        )
        return header + "\n".join(view)

    @tool
    def get_router_config(router_name: str, section: str = "export") -> str:
        """
        Baca konfigurasi router MikroTik via SSH.
        Bisa membaca seluruh konfigurasi (export) atau subseksi tertentu.
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
            section: Bagian konfigurasi yang ingin dibaca. Pilihan:
                'export'            — seluruh konfigurasi (bisa besar, akan dipotong)
                'ip-address'        — daftar IP address per interface
                'ip-pool'           — DHCP IP pool
                'ip-route'          — routing table aktif (termasuk dynamic/connected routes)
                'routing-static'    — KONFIGURASI static route yang dikonfigurasi admin
                'routing-ospf'      — konfigurasi protokol OSPF
                'routing-bgp'       — konfigurasi protokol BGP
                'routing-filter'    — routing filter/policy
                'interface'         — semua interface
                'bridge'            — bridge interface
                'dhcp-server'       — konfigurasi DHCP server
                'dhcp-network'      — network DHCP server
                'firewall-filter'   — firewall filter rules
                'firewall-nat'      — firewall NAT rules
                'vlan'              — VLAN interface
                'dns'               — konfigurasi DNS
                'ntp'               — konfigurasi NTP client
                'users'             — daftar user
                'ip-neighbor'       — perangkat yang terdeteksi langsung via LLDP/CDP (direct connect)
                'ip-neighbor-detail'— detail lengkap perangkat direct connect (LLDP/CDP)
                'ip-arp'            — ARP table (IP-to-MAC mapping perangkat di jaringan lokal)
        """
        router_name = _validate_router(router_name)
        entry = _NAME_TO_ENTRIES[router_name][0]
        creds = _ssh_creds()
        ros = entry["ros_version"]

        section = section.strip().lower()

        # Map section names to commands for v7 and v6
        _SECTION_MAP: dict[str, tuple[str, str]] = {
            "export":          ("/export",                           "export"),
            "ip-address":      ("/ip/address/print",                 "ip address print"),
            "ip-pool":         ("/ip/pool/print",                    "ip pool print"),
            "ip-route":        ("/ip/route/print",                   "ip route print"),
            "routing-static":  ("/ip/route/print where static",      "ip route print where static"),
            "routing-ospf":    ("/routing/ospf/instance/print",      "routing ospf instance print"),
            "routing-bgp":     ("/routing/bgp/connection/print",     "routing bgp instance print"),
            "routing-filter":  ("/routing/filter/rule/print",        "routing filter print"),
            "interface":       ("/interface/print",                  "interface print"),
            "bridge":          ("/interface/bridge/print",           "interface bridge print"),
            "dhcp-server":     ("/ip/dhcp-server/print",             "ip dhcp-server print"),
            "dhcp-network":    ("/ip/dhcp-server/network/print",     "ip dhcp-server network print"),
            "firewall-filter": ("/ip/firewall/filter/print",         "ip firewall filter print"),
            "firewall-nat":    ("/ip/firewall/nat/print",            "ip firewall nat print"),
            "vlan":            ("/interface/vlan/print",             "interface vlan print"),
            "dns":             ("/ip/dns/print",                     "ip dns print"),
            "ntp":             ("/system/ntp/client/print",          "system ntp client print"),
            "users":           ("/user/print",                       "user print"),
            "ip-neighbor":     ("/ip/neighbor/print",                "ip neighbor print"),
            "ip-arp":          ("/ip/arp/print",                     "ip arp print"),
            "ip-neighbor-detail": ("/ip/neighbor/print detail",      "ip neighbor print detail"),
        }

        if section not in _SECTION_MAP:
            valid = ", ".join(sorted(_SECTION_MAP.keys()))
            return f"Section '{section}' tidak valid. Pilihan: {valid}"

        cmd_v7, cmd_v6 = _SECTION_MAP[section]
        cmd = cmd_v7 if ros == 7 else cmd_v6

        ok, out, err = ssh_run_command(
            host=entry["host"],
            username=creds["username"],
            password=creds["password"],
            command=cmd,
            port=creds["port"],
            timeout=creds["timeout"],
        )

        if not ok:
            return f"Gagal ambil konfigurasi dari {router_name} ({entry['host']}): {err}"

        if not out.strip():
            return f"Tidak ada output untuk section '{section}' di {router_name}."

        output = out.strip()
        header = f"Konfigurasi {router_name} ({entry['host']}) — section: {section}\n{'─'*60}\n"

        # Truncate large outputs (full export can be huge)
        limit = 6000 if section == "export" else 4000
        if len(output) > limit:
            output = (
                output[:limit]
                + f"\n\n...[output terpotong, total {len(out)} karakter. "
                f"Gunakan section lebih spesifik untuk detail.]..."
            )

        return header + output

    @tool
    def get_routing_full(router_name: str) -> str:
        """
        Cek konfigurasi routing LENGKAP di router: static route, OSPF, BGP, routing filter,
        dan routing table aktif. Gunakan ini saat diminta 'cek routing' atau 'cek konfigurasi
        routing' agar tidak melewatkan protokol routing yang mungkin berjalan di router.
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        """
        router_name = _validate_router(router_name)
        entry = _NAME_TO_ENTRIES[router_name][0]
        creds = _ssh_creds()
        ros = entry["ros_version"]

        sections_v7 = [
            ("Static Routes",     "/ip/route/print where static"),
            ("Active Routes",     "/ip/route/print"),
            ("OSPF Instances",    "/routing/ospf/instance/print"),
            ("OSPF Areas",        "/routing/ospf/area/print"),
            ("OSPF Interfaces",   "/routing/ospf/interface-template/print"),
            ("BGP Connections",   "/routing/bgp/connection/print"),
            ("Routing Filters",   "/routing/filter/rule/print"),
        ]
        sections_v6 = [
            ("Static Routes",     "ip route print where static"),
            ("Active Routes",     "ip route print"),
            ("OSPF Instances",    "routing ospf instance print"),
            ("OSPF Networks",     "routing ospf network print"),
            ("BGP Instances",     "routing bgp instance print"),
            ("BGP Peers",         "routing bgp peer print"),
            ("Routing Filters",   "routing filter print"),
        ]

        sections = sections_v7 if ros == 7 else sections_v6
        lines = [f"Konfigurasi Routing Lengkap — {router_name} ({entry['host']}) ROS v{ros}"]
        lines.append("═" * 60)

        has_any = False
        for label, cmd in sections:
            ok, out, err = ssh_run_command(
                host=entry["host"],
                username=creds["username"],
                password=creds["password"],
                command=cmd,
                port=creds["port"],
                timeout=creds["timeout"],
            )
            lines.append(f"\n── {label} ──")
            if not ok:
                lines.append(f"  [gagal: {err[:60]}]")
            elif not out.strip():
                lines.append("  (tidak ada konfigurasi)")
            else:
                output = out.strip()
                # Limit per-section to 800 chars
                if len(output) > 800:
                    output = output[:800] + f"\n  ...[+{len(out)-800} karakter]"
                lines.append(output)
                has_any = True

        if not has_any:
            lines.append("\nTidak ada konfigurasi routing ditemukan di router ini.")

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

    @tool
    def get_current_time() -> str:
        """
        Dapatkan waktu dan tanggal saat ini (WIB, UTC+7).
        Gunakan ini saat ditanya jam berapa sekarang, tanggal berapa, hari apa,
        atau untuk menghitung selisih waktu dari jadwal ujian.
        Tidak memerlukan argumen.
        """
        WIB = timezone(timedelta(hours=7))
        now = datetime.now(WIB)
        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        month_names = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        ]
        return (
            f"Waktu saat ini (WIB):\n"
            f"  Hari    : {day_names[now.weekday()]}\n"
            f"  Tanggal : {now.day:02d} {month_names[now.month - 1]} {now.year}\n"
            f"  Jam     : {now.strftime('%H:%M:%S')} WIB\n"
            f"  ISO     : {now.isoformat()}"
        )

    @tool
    def list_reports() -> str:
        """
        Tampilkan daftar file laporan (.md) yang tersedia di direktori laporan/.
        Gunakan ini untuk mengetahui tanggal-tanggal yang tersedia sebelum memanggil read_report().
        Tidak memerlukan argumen.
        """
        laporan_dir = WORKDIR / "laporan"
        if not laporan_dir.exists():
            return "Direktori laporan/ tidak ditemukan."
        files = sorted(laporan_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
        if not files:
            return "Belum ada laporan tersedia."
        lines = [f"Laporan tersedia ({len(files)} file):"]
        for f in files[:20]:
            size_kb = f.stat().st_size / 1024
            lines.append(f"  {f.name}  ({size_kb:.1f} KB)")
        return "\n".join(lines)

    @tool
    def read_report(filename: str) -> str:
        """
        Baca isi file laporan dari direktori laporan/.
        Gunakan list_reports() untuk mengetahui nama file yang tersedia.
        Untuk laporan terbaru, gunakan 'latest' sebagai filename.
        Args:
            filename: Nama file laporan (contoh: dhcp-lease-20260424.md) atau 'latest' untuk terbaru.
        """
        laporan_dir = WORKDIR / "laporan"
        if not laporan_dir.exists():
            return "Direktori laporan/ tidak ditemukan."

        if filename.strip().lower() == "latest":
            files = sorted(laporan_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                return "Belum ada laporan tersedia."
            target = files[0]
        else:
            # Sanitize: only allow filename characters, no path traversal
            safe_name = Path(filename).name
            target = laporan_dir / safe_name
            if not target.exists():
                available = [f.name for f in sorted(laporan_dir.glob("*.md"))[-5:]]
                return (
                    f"File '{safe_name}' tidak ditemukan.\n"
                    f"File terbaru: {', '.join(available)}"
                )
            # Security: ensure resolved path stays inside laporan_dir
            if not target.resolve().is_relative_to(laporan_dir.resolve()):
                return "Error: akses file di luar direktori laporan tidak diizinkan."

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"Gagal membaca {target.name}: {e}"

        # Return up to 8000 chars to fit in context
        if len(content) > 8000:
            return (
                f"=== {target.name} (8000/{len(content)} karakter) ===\n"
                + content[:8000]
                + f"\n...[terpotong, laporan penuh {len(content)} karakter. "
                f"Minta bagian spesifik jika perlu.]..."
            )
        return f"=== {target.name} ===\n{content}"

    @tool
    def read_report_section(filename: str, section: str) -> str:
        """
        Baca satu section spesifik dari laporan berdasarkan nomor atau kata kunci judul.
        Lebih efisien dari read_report() karena hanya mengambil bagian yang relevan.
        Gunakan ini saat laporan terlalu panjang atau ingin membaca section tertentu.
        Args:
            filename: Nama file laporan (contoh: dhcp-lease-20260425.md) atau 'latest'.
            section: Nomor section (contoh: '7', '8', '9') atau kata kunci judul
                     (contoh: 'anomali', 'utbk', 'rekomendasi', 'router', 'disconnect').
        """
        laporan_dir = WORKDIR / "laporan"
        if not laporan_dir.exists():
            return "Direktori laporan/ tidak ditemukan."

        if filename.strip().lower() == "latest":
            files = sorted(laporan_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                return "Belum ada laporan tersedia."
            target = files[0]
        else:
            safe_name = Path(filename).name
            target = laporan_dir / safe_name
            if not target.exists():
                return f"File '{safe_name}' tidak ditemukan."
            if not target.resolve().is_relative_to(laporan_dir.resolve()):
                return "Error: akses file di luar direktori laporan tidak diizinkan."

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"Gagal membaca {target.name}: {e}"

        import re as _re

        # Split into sections by "## " headings
        # Find all section positions
        section_pattern = _re.compile(r'^(#{1,3} .+)$', _re.MULTILINE)
        matches = list(section_pattern.finditer(content))

        if not matches:
            return f"Tidak ada section ditemukan di {target.name}."

        # Try to match by number (e.g. '7', '8') or keyword
        section = section.strip()
        target_idx = None

        # Match by number: "## 7." or "## 7 "
        if section.isdigit():
            num_re = _re.compile(rf'^#{1,3} {_re.escape(section)}[\.\s]', _re.MULTILINE)
            for i, m in enumerate(matches):
                heading = content[m.start():m.end()]
                if num_re.match(heading):
                    target_idx = i
                    break

        # Match by keyword in heading (case-insensitive)
        if target_idx is None:
            kw = section.lower()
            for i, m in enumerate(matches):
                heading = content[m.start():m.end()].lower()
                if kw in heading:
                    target_idx = i
                    break

        if target_idx is None:
            # Show available sections as TOC
            toc = [f"Section '{section}' tidak ditemukan di {target.name}."]
            toc.append("Section yang tersedia:")
            for m in matches:
                heading = content[m.start():m.end()]
                if heading.startswith("## "):
                    toc.append(f"  {heading}")
            return "\n".join(toc)

        # Extract content from this section to the next same-level section
        start_pos = matches[target_idx].start()
        end_pos = len(content)
        heading_level = len(matches[target_idx].group().split(' ')[0])  # count '#'

        for j in range(target_idx + 1, len(matches)):
            next_heading = matches[j].group()
            next_level = len(next_heading.split(' ')[0])
            if next_level <= heading_level:
                end_pos = matches[j].start()
                break

        section_content = content[start_pos:end_pos].strip()

        # Limit to 6000 chars if still large
        if len(section_content) > 6000:
            section_content = (
                section_content[:6000]
                + f"\n...[terpotong, section ini {len(section_content)} karakter]..."
            )

        return f"=== {target.name} ===\n{section_content}"

    @tool
    def get_report_toc(filename: str) -> str:
        """
        Ambil daftar isi (table of contents) dari laporan — hanya judul section.
        Gunakan ini PERTAMA KALI sebelum membaca section tertentu, untuk mengetahui
        semua section yang tersedia tanpa perlu membaca seluruh isi laporan.
        Args:
            filename: Nama file laporan (contoh: dhcp-lease-20260425.md) atau 'latest'.
        """
        laporan_dir = WORKDIR / "laporan"
        if not laporan_dir.exists():
            return "Direktori laporan/ tidak ditemukan."

        if filename.strip().lower() == "latest":
            files = sorted(laporan_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                return "Belum ada laporan tersedia."
            target = files[0]
        else:
            safe_name = Path(filename).name
            target = laporan_dir / safe_name
            if not target.exists():
                return f"File '{safe_name}' tidak ditemukan."
            if not target.resolve().is_relative_to(laporan_dir.resolve()):
                return "Error: akses file di luar direktori laporan tidak diizinkan."

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"Gagal membaca {target.name}: {e}"

        import re as _re
        heading_re = _re.compile(r'^(#{1,3} .+)$', _re.MULTILINE)
        headings = heading_re.findall(content)

        if not headings:
            return f"Tidak ada heading ditemukan di {target.name}."

        lines = [f"Daftar isi {target.name} ({len(content):,} karakter total):"]
        for h in headings:
            # indent sub-headings
            level = len(h) - len(h.lstrip('#'))
            indent = "  " * (level - 1)
            lines.append(f"{indent}{h.lstrip('#').strip()}")

        lines.append("")
        lines.append("Gunakan read_report_section(filename, '<nomor>') untuk membaca tiap section.")
        return "\n".join(lines)

    @tool
    def run_command(router_name: str, command: str) -> str:
        """
        Jalankan perintah MikroTik baca-saja (read-only) secara langsung di router.
        Gunakan untuk verifikasi, cross-check, atau cek hal spesifik yang tidak
        tercakup oleh tools lain.
        Contoh perintah valid:
            '/user/print'
            'user print where name=netadmin'
            '/ip/address/print where interface=ether1'
            '/system/identity/print'
            'ip neighbor print'
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
            command: Perintah MikroTik read-only yang akan dieksekusi.
        """
        router_name = _validate_router(router_name)

        # Security: block write/destructive keywords
        _BLOCKED = [
            "remove", "delete", " set ", "=set", "/set",
            " add ", "=add", "/add",
            "move", "enable", "disable",
            "reset", "reboot", "shutdown", "format",
            "export sensitive", "password",
        ]
        cmd_lower = command.lower()
        for blocked in _BLOCKED:
            if blocked in cmd_lower:
                return (
                    f"Error: perintah ditolak — mengandung kata terlarang '{blocked.strip()}'. "
                    f"Hanya perintah read-only yang diizinkan."
                )

        entry = _NAME_TO_ENTRIES[router_name][0]
        creds = _ssh_creds()

        ok, out, err = ssh_run_command(
            host=entry["host"],
            username=creds["username"],
            password=creds["password"],
            command=command.strip(),
            port=creds["port"],
            timeout=creds["timeout"],
        )

        if not ok:
            return f"Gagal menjalankan perintah di {router_name} ({entry['host']}): {err}"

        if not out.strip():
            return f"Perintah '{command}' tidak menghasilkan output di {router_name}."

        output = out.strip()
        header = f"Output dari {router_name} ({entry['host']}) — `{command}`\n{'─'*60}\n"

        if len(output) > 4000:
            output = output[:4000] + f"\n...[terpotong, total {len(out)} karakter]..."

        return header + output

    @tool
    def run_diagnostic(router_name: str, tool_name: str, target: str, count: int = 4) -> str:
        """
        Jalankan perintah diagnostik jaringan di router MikroTik (ping, traceroute, dll).
        Menggunakan timeout yang lebih panjang (60 detik) dibanding run_command().
        Gunakan tool ini untuk:
        - traceroute: tool_name='traceroute', target='10.1.1.1'
        - ping       : tool_name='ping',       target='10.1.1.1', count=5
        - bandwidth  : tool_name='bandwidth-test' (hanya jika diizinkan)
        Args:
            router_name: Nama router. Gunakan list_routers() untuk daftar valid.
            tool_name:   Nama tool diagnostik: 'traceroute', 'ping', 'flood-ping'.
            target:      IP address atau hostname tujuan.
            count:       Jumlah paket ping atau hop maksimal traceroute (default 4, maks 30).
        """
        router_name = _validate_router(router_name)

        # Validate target - basic IP/hostname check, reject shell metacharacters
        if re.search(r'[|;&$`\\"\'\s]', target):
            return "Error: karakter tidak valid dalam target address."
        if not target:
            return "Error: target address kosong."

        # Validate tool name
        allowed_tools = {"traceroute", "ping", "flood-ping"}
        tool_name = tool_name.strip().lower()
        if tool_name not in allowed_tools:
            return (
                f"Tool '{tool_name}' tidak diizinkan. "
                f"Pilihan: {', '.join(sorted(allowed_tools))}"
            )

        entry = _NAME_TO_ENTRIES[router_name][0]
        creds = _ssh_creds()
        ros = entry["ros_version"]
        count = max(1, min(int(count), 30))

        # Build command based on ROS version and tool
        if tool_name == "traceroute":
            if ros == 7:
                cmd = f"/tool/traceroute address={target} count={count}"
            else:
                cmd = f"tool traceroute {target} count={count}"
        elif tool_name == "ping":
            if ros == 7:
                cmd = f"/ping address={target} count={count}"
            else:
                cmd = f"ping {target} count={count}"
        elif tool_name == "flood-ping":
            if ros == 7:
                cmd = f"/ping address={target} count={count} interval=0"
            else:
                cmd = f"ping {target} count={count} interval=0"
        else:
            cmd = f"tool {tool_name} {target}"

        # Use extended timeout: 60 seconds for diagnostics
        diag_timeout = 60

        ok, out, err = ssh_run_command(
            host=entry["host"],
            username=creds["username"],
            password=creds["password"],
            command=cmd,
            port=creds["port"],
            timeout=diag_timeout,
        )

        if not ok:
            return (
                f"Gagal menjalankan {tool_name} di {router_name} ({entry['host']}): {err}\n"
                f"Perintah: {cmd}"
            )

        if not out.strip():
            return f"Tidak ada output dari {tool_name} ke {target} di {router_name}."

        header = (
            f"Hasil {tool_name} dari {router_name} ({entry['host']}) ke {target}\n"
            f"Perintah: {cmd}\n"
            f"{'─' * 60}\n"
        )

        output = out.strip()
        if len(output) > 3000:
            output = output[:3000] + f"\n...[terpotong, total {len(out)} karakter]..."

        return header + output

    @tool
    def run_command_all_routers(command: str) -> str:
        """
        Jalankan perintah MikroTik read-only yang SAMA di SEMUA router secara paralel.
        Gunakan ini untuk audit/cek menyeluruh seperti:
        - cek keberadaan user di semua router: command = '/user/print where name=netadmin'
        - cek konfigurasi DNS: command = '/ip/dns/print'
        - cek NTP: command = '/system/ntp/client/print'
        - cek identity: command = '/system/identity/print'
        Jauh lebih efisien dari memanggil run_command() satu per satu.
        Args:
            command: Perintah MikroTik read-only. Untuk ROS v6, command tanpa '/' akan digunakan.
                     Tool ini otomatis menyesuaikan command untuk ROS v6 (tanpa leading slash).
        """
        # Security: block write/destructive keywords
        _BLOCKED = [
            "remove", "delete", " set ", "=set", "/set",
            " add ", "=add", "/add",
            "move", "enable", "disable",
            "reset", "reboot", "shutdown", "format",
            "export sensitive", "password",
        ]
        cmd_lower = command.lower()
        for blocked in _BLOCKED:
            if blocked in cmd_lower:
                return (
                    f"Error: perintah ditolak — mengandung kata terlarang '{blocked.strip()}'. "
                    f"Hanya perintah read-only yang diizinkan."
                )

        # Get one entry per unique router name
        seen_names: set[str] = set()
        unique_entries: list[dict[str, Any]] = []
        for entry in _ROUTERS:
            if entry["name"] not in seen_names:
                seen_names.add(entry["name"])
                unique_entries.append(entry)

        def _check_one(entry: dict[str, Any]) -> dict[str, Any]:
            creds = _ssh_creds()
            # Auto-adapt command for ROS v6: strip leading '/'
            cmd = command.strip()
            if entry["ros_version"] == 6 and cmd.startswith("/"):
                # Convert /ip/dns/print -> ip dns print
                cmd = cmd.lstrip("/").replace("/", " ")

            ok, out, err = ssh_run_command(
                host=entry["host"],
                username=creds["username"],
                password=creds["password"],
                command=cmd,
                port=creds["port"],
                timeout=creds["timeout"],
            )
            return {
                "name": entry["name"],
                "host": entry["host"],
                "ok": ok,
                "out": out.strip() if ok else "",
                "err": err if not ok else "",
            }

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_check_one, e): e for e in unique_entries}
            for future in as_completed(futures, timeout=120):
                try:
                    results.append(future.result())
                except Exception as exc:
                    entry = futures[future]
                    results.append({
                        "name": entry["name"],
                        "host": entry["host"],
                        "ok": False,
                        "out": "",
                        "err": str(exc),
                    })

        results.sort(key=lambda x: x["name"])

        lines = [f"Hasil `{command}` di semua router ({len(results)} router):\n"]
        ok_count = sum(1 for r in results if r["ok"] and r["out"])
        empty_count = sum(1 for r in results if r["ok"] and not r["out"])
        fail_count = sum(1 for r in results if not r["ok"])
        lines.append(f"Ringkasan: {ok_count} ada output, {empty_count} output kosong, {fail_count} gagal\n")
        lines.append("─" * 60)

        for r in results:
            lines.append(f"\n[{r['name']}] ({r['host']})")
            if not r["ok"]:
                lines.append(f"  ✗ GAGAL: {r['err'][:80]}")
            elif not r["out"]:
                lines.append(f"  (tidak ada output / tidak ditemukan)")
            else:
                # Limit per-router output to 300 chars
                preview = r["out"][:300]
                if len(r["out"]) > 300:
                    preview += f"  ...[+{len(r['out'])-300} karakter]"
                lines.append(preview)

        return "\n".join(lines)

    _TOOLS = [
        list_routers,
        check_reachability,
        get_system_info,
        get_dhcp_leases,
        get_all_leases_for_router,
        get_router_config,
        get_routing_full,
        get_router_log,
        audit_all_routers,
        search_device,
        get_current_time,
        list_reports,
        get_report_toc,
        read_report,
        read_report_section,
        run_command,
        run_diagnostic,
        run_command_all_routers,
    ]

    def _build_system_prompt() -> str:
        WIB = timezone(timedelta(hours=7))
        now = datetime.now(WIB)
        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        month_names = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        ]
        current_time_str = (
            f"{day_names[now.weekday()]}, "
            f"{now.day:02d} {month_names[now.month - 1]} {now.year}, "
            f"pukul {now.strftime('%H:%M')} WIB"
        )
        return (
            f"Waktu saat ini: {current_time_str}.\n"
            "Kamu adalah network engineer AI yang dapat melakukan monitoring dan audit "
            "jaringan DHCP pada perangkat MikroTik untuk ujian UTBK 2026. "
            "Kamu memiliki akses SSH ke semua router melalui tools yang tersedia. "
            "Kredensial SSH ditangani secara internal — jangan pernah meminta password kepada pengguna. "
            "Jika tidak yakin nama router yang valid, panggil list_routers() terlebih dahulu. "
            "Gunakan tools untuk mendapatkan data live saat ditanya tentang kondisi terkini. "
            "Untuk melihat log router, gunakan get_router_log(router_name, topic) — "
            "topic bisa: 'dhcp', 'system', 'error', 'warning', atau kosong untuk semua log. "
            "Untuk membaca konfigurasi router, gunakan get_router_config(router_name, section) — "
            "section: 'export' (semua), 'ip-address', 'ip-pool', 'interface', 'dhcp-server', "
            "'firewall-filter', 'firewall-nat', 'vlan', 'bridge', 'dns', 'ntp', 'users', "
            "'ip-route' (routing table aktif), 'routing-static' (konfigurasi static route), "
            "'routing-ospf', 'routing-bgp', 'routing-filter'. "
            "PENTING: untuk 'cek routing' atau 'cek konfigurasi routing', SELALU gunakan "
            "get_routing_full(router_name) — tool ini mengecek semua protokol routing sekaligus "
            "(static, OSPF, BGP, filter). Jangan hanya cek routing-static saja. "
            "PENTING: 'neighbor' atau 'perangkat direct connect' atau 'ip neighbor' merujuk pada "
            "perangkat fisik yang terhubung langsung via LLDP/CDP — gunakan "
            "get_router_config(router_name, 'ip-neighbor') atau 'ip-arp' untuk ARP table. "
            "JANGAN gunakan OSPF neighbor untuk pertanyaan ini. "
            "Gunakan tool get_current_time() jika perlu waktu yang lebih presisi atau terkini. "
            "Laporan harian berukuran besar (>60KB). "
            "JANGAN gunakan read_report() untuk melihat daftar section — laporan terlalu panjang dan akan terpotong. "
            "Untuk melihat semua section laporan, SELALU gunakan get_report_toc(filename) terlebih dahulu. "
            "Untuk membaca isi section tertentu, gunakan read_report_section(filename, section) "
            "(contoh: read_report_section('latest', '8') untuk section 8). "
            "Gunakan read_report() hanya jika laporan pendek atau perlu header/ringkasan awal saja. "
            "Jawab dalam Bahasa Indonesia. "
            "Gunakan istilah teknis jaringan dalam bahasa Inggris dengan backtick: "
            "`bound`, `waiting`, `lease`, `DHCP`, `IP`, `MAC`, `router`, `subnet`. "
            "Untuk traceroute, ping, atau diagnostik jaringan dari router, gunakan run_diagnostic() "
            "bukan run_command() — karena diagnostik butuh timeout lebih panjang (60 detik). "
            "Contoh: run_diagnostic('DTI', 'traceroute', '10.1.1.47'). "
            "Jika diminta cek sesuatu di SEMUA router sekaligus, gunakan run_command_all_routers(command) "
            "untuk efisiensi — jauh lebih cepat dari memanggil run_command() satu per satu. "
            "Jika hasil tool menunjukkan error, timeout, atau output kosong, WAJIB coba ulang "
            "dengan tool yang sama atau gunakan run_command() untuk verifikasi langsung. "
            "Jangan simpulkan hasil yang tidak pasti tanpa melakukan verifikasi ulang terlebih dahulu. "
            "Jika setelah 2 kali percobaan masih gagal, nyatakan secara eksplisit bahwa "
            "router tersebut tidak dapat dijangkau atau data tidak tersedia. "
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
        # num_predict=1024,
        num_predict=4096,
        timeout=300, # 5 menit
        num_ctx=32768, # context window
        # stop=["<think>", "</think>"], # Paksa model stop jika mulai "berpikir"
    )
    memory = MemorySaver()
    agent = create_react_agent(
        llm,
        tools=_TOOLS,
        checkpointer=memory,
        prompt=_build_system_prompt(),
    )
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50,
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
