"""Tools: routing table, OSPF, BGP — read-only."""

from __future__ import annotations

import re

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_creds_for, ssh_run_command


def _parse_bgp_sessions(raw: str) -> list[dict]:
    """Parse output /routing/bgp/session/print menjadi list of dict."""
    sessions: list[dict] = []
    cur: dict = {}

    for line in raw.splitlines():
        # Baris header sesi: " 0 E name=..." atau " 23   name=..."
        m = re.match(r'^\s*(\d+)\s+(E?)\s*name="([^"]+)"', line)
        if m:
            if cur:
                sessions.append(cur)
            cur = {
                "idx":          int(m.group(1)),
                "established":  m.group(2).strip() == "E",
                "name":         m.group(3),
                "remote_as":    "",
                "remote_addr":  "",
                "local_as":     "",
                "local_addr":   "",
                "bgp_type":     "",
                "uptime":       "—",
                "prefix_count": 0,
                "last_stopped": "—",
            }
            continue

        if not cur:
            continue

        s = line.strip()

        if s.startswith("remote.address="):
            m2 = re.search(r'remote\.address=(\S+)', s)
            if m2:
                cur["remote_addr"] = m2.group(1)
            m3 = re.search(r'\.as=(\d+)', s)
            if m3:
                cur["remote_as"] = m3.group(1)

        if s.startswith("local.") and ".as=" in s:
            m_la = re.search(r'local\.address=(\S+)', s)
            if m_la:
                cur["local_addr"] = m_la.group(1).split("/")[0]
            m4 = re.search(r'local(?:\.role=\S+)?\s+\.address=\S+\s+\.as=(\d+)', s)
            if not m4:
                m4 = re.search(r'\.as=(\d+)', s)
            if m4:
                cur["local_as"] = m4.group(1)

        if "uptime=" in s:
            m5 = re.search(r'uptime=(\S+)', s)
            if m5:
                raw = m5.group(1)
                # Strip trailing milliseconds like "930ms" from MikroTik output
                cur["uptime"] = re.sub(r'\d+ms$', '', raw) or "—"

        if "last-stopped=" in s:
            # MikroTik datetime: "mar/11/2026 21:17:07" (has space between date and time)
            m_ls = re.search(r'last-stopped=(\S+\s+\d{2}:\d{2}:\d{2})', s)
            if not m_ls:
                m_ls = re.search(r'last-stopped=(\S+)', s)
            if m_ls:
                cur["last_stopped"] = m_ls.group(1).strip()

        if "prefix-count=" in s:
            m6 = re.search(r'prefix-count=(\d+)', s)
            if m6:
                cur["prefix_count"] = int(m6.group(1))

        if s.endswith("ebgp") or " ebgp" in s:
            cur["bgp_type"] = "eBGP"
        elif s.endswith("ibgp") or " ibgp" in s:
            cur["bgp_type"] = "iBGP"

    if cur:
        sessions.append(cur)

    return sessions


def _parse_ospf_neighbors(raw: str) -> list[dict]:
    """Parse output /routing/ospf/neighbor/print menjadi list of dict."""
    neighbors: list[dict] = []
    cur: dict = {}

    for line in raw.splitlines():
        m = re.match(r'^\s*(\d+)\s+', line)
        if m and ("instance=" in line or "address=" in line):
            if cur:
                neighbors.append(cur)
            cur = {
                "idx":       int(m.group(1)),
                "instance":  "",
                "area":      "",
                "address":   "",
                "router_id": "",
                "state":     "",
                "adjacency": "—",
                "state_changes": 0,
            }
            s = line.strip()
            for field in ("instance", "area", "address", "router-id",
                          "state", "state-changes", "adjacency"):
                fm = re.search(rf'{field}=("([^"]+)"|(\S+))', s)
                if fm:
                    val = fm.group(2) or fm.group(3)
                    key = field.replace("-", "_")
                    if key == "router_id":
                        cur["router_id"] = val
                    elif key == "state_changes":
                        cur["state_changes"] = int(val) if val.isdigit() else 0
                    elif key in cur:
                        cur[key] = val
            continue

        if not cur:
            continue

        s = line.strip()
        for field in ("instance", "area", "address", "router-id",
                      "state", "state-changes", "adjacency"):
            fm = re.search(rf'{field}=("([^"]+)"|(\S+))', s)
            if fm:
                val = fm.group(2) or fm.group(3)
                key = field.replace("-", "_")
                if key == "router_id":
                    cur["router_id"] = val
                elif key == "state_changes":
                    cur["state_changes"] = int(val) if val.isdigit() else 0
                elif key in cur:
                    cur[key] = val

    if cur:
        neighbors.append(cur)

    return neighbors


@tool
def get_routing_full(router_name: str) -> str:
    """
    Cek konfigurasi routing LENGKAP: static route, OSPF, BGP, routing filter,
    dan routing table aktif. Gunakan saat diminta 'cek routing' atau
    'cek konfigurasi routing' agar tidak melewatkan protokol yang berjalan.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds_for(entry)
    ros = entry["ros_version"]

    sections_v7 = [
        ("Static Routes",   "/ip/route/print where static"),
        ("Active Routes",   "/ip/route/print"),
        ("OSPF Instances",  "/routing/ospf/instance/print"),
        ("OSPF Areas",      "/routing/ospf/area/print"),
        ("OSPF Interfaces", "/routing/ospf/interface-template/print"),
        ("BGP Connections", "/routing/bgp/connection/print"),
        ("Routing Filters", "/routing/filter/rule/print"),
    ]
    sections_v6 = [
        ("Static Routes",   "ip route print where static"),
        ("Active Routes",   "ip route print"),
        ("OSPF Instances",  "routing ospf instance print"),
        ("OSPF Networks",   "routing ospf network print"),
        ("BGP Instances",   "routing bgp instance print"),
        ("BGP Peers",       "routing bgp peer print"),
        ("Routing Filters", "routing filter print"),
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
            if len(output) > 5000:
                output = output[:5000] + f"\n  ...[+{len(out)-5000} karakter]"
            lines.append(output)
            has_any = True

    if not has_any:
        lines.append("\nTidak ada konfigurasi routing ditemukan di router ini.")
    return "\n".join(lines)


@tool
def get_bgp_sessions(router_name: str) -> str:
    """
    Ambil status semua BGP session di satu router: state (established/down),
    remote AS, remote IP, uptime, dan prefix count. Hasilnya ringkas dan lengkap
    meski jumlah sesi banyak. Gunakan untuk diagnosis BGP dan monitoring peering.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds_for(entry)
    ros = entry["ros_version"]

    cmd = "/routing/bgp/session/print" if ros == 7 else "routing bgp peer print"
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal ambil BGP session dari {router_name}: {err}"
    if not out.strip():
        return f"Tidak ada BGP session di {router_name}."

    sessions = _parse_bgp_sessions(out)
    if not sessions:
        return f"Tidak dapat mem-parse BGP session output dari {router_name}:\n{out[:500]}"

    est   = sum(1 for s in sessions if s["established"])
    down  = len(sessions) - est
    local_as = sessions[0]["local_as"] if sessions else "?"

    lines = [
        f"BGP Sessions — {router_name} ({entry['host']})  Local AS: {local_as}",
        f"Total: {len(sessions)}  Established: {est}  Down: {down}",
        "─" * 80,
        f"{'#':>3}  {'St':4}  {'Type':5}  {'RemAS':>7}  {'RemoteIP':<24}  {'Uptime':<16}  {'Pfx':>6}  Name",
        "─" * 80,
    ]
    for s in sessions:
        st = "✓EST" if s["established"] else "✗DWN"
        name_short = s["name"][:42]
        lines.append(
            f"{s['idx']:>3}  {st}  {s['bgp_type'] or '?':5}  {s['remote_as']:>7}  "
            f"{s['remote_addr']:<24}  {s['uptime']:<16}  {s['prefix_count']:>6}  {name_short}"
        )

    if down:
        lines.append("")
        lines.append(f"⚠ {down} session DOWN:")
        for s in sessions:
            if not s["established"]:
                stopped = f"  last-stopped: {s['last_stopped']}" if s["last_stopped"] != "—" else ""
                lines.append(
                    f"  - #{s['idx']} {s['name']}  (remote: {s['remote_addr']} AS{s['remote_as']}){stopped}"
                )

    return "\n".join(lines)


@tool
def get_ospf_neighbors(router_name: str) -> str:
    """
    Ambil status semua OSPF neighbor di satu router: state, router-id, area,
    adjacency uptime. Gunakan untuk diagnosis OSPF adjacency dan monitoring
    routing interior.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds_for(entry)
    ros = entry["ros_version"]

    cmd = "/routing/ospf/neighbor/print" if ros == 7 else "routing ospf neighbor print"
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal ambil OSPF neighbor dari {router_name}: {err}"
    if not out.strip():
        return f"Tidak ada OSPF neighbor di {router_name}."

    neighbors = _parse_ospf_neighbors(out)
    if not neighbors:
        return f"Tidak dapat mem-parse OSPF neighbor output dari {router_name}:\n{out[:500]}"

    full  = sum(1 for n in neighbors if n["state"].lower() == "full")
    total = len(neighbors)

    # Flag neighbors with high state-changes (>20) even if Full
    high_sc = [n for n in neighbors if int(n["state_changes"]) > 20]

    lines = [
        f"OSPF Neighbors — {router_name} ({entry['host']})",
        f"Total: {total}  Full: {full}  Masalah: {total - full}",
        "─" * 80,
        f"{'#':>3}  {'State':<8}  {'Address':<18}  {'RouterID':<18}  {'SC':>4}  {'Adjacency':<16}  Area",
        "─" * 80,
    ]
    for n in neighbors:
        state_icon = "✓" if n["state"].lower() == "full" else "⚠"
        sc_val = str(n["state_changes"]) if n["state_changes"] else "—"
        lines.append(
            f"{n['idx']:>3}  {state_icon}{n['state']:<7}  {n['address']:<18}  "
            f"{n['router_id']:<18}  {sc_val:>4}  {n['adjacency']:<16}  {n['area']}"
        )

    if total > full:
        lines.append("")
        lines.append(f"⚠ Neighbor tidak FULL:")
        for n in neighbors:
            if n["state"].lower() != "full":
                lines.append(
                    f"  - #{n['idx']} {n['address']} (RouterID: {n['router_id']}) "
                    f"state={n['state']} state-changes={n['state_changes']} adjacency={n['adjacency']}"
                )

    if high_sc:
        lines.append("")
        lines.append(f"⚠ Neighbor Full tapi state-changes tinggi (>20) — riwayat instabilitas:")
        for n in high_sc:
            lines.append(
                f"  - #{n['idx']} {n['address']} (RouterID: {n['router_id']}) "
                f"state-changes={n['state_changes']} adjacency={n['adjacency']}"
            )

    return "\n".join(lines)


@tool
def get_router_config(router_name: str, section: str = "export") -> str:
    """
    Baca konfigurasi router MikroTik via SSH.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        section: Bagian konfigurasi. Pilihan:
            'export'             — seluruh konfigurasi
            'ip-address'         — daftar IP address per interface
            'ip-pool'            — DHCP IP pool
            'ip-route'           — routing table aktif
            'routing-static'     — static route yang dikonfigurasi
            'routing-ospf'       — konfigurasi OSPF
            'routing-bgp'        — konfigurasi BGP
            'routing-filter'     — routing filter/policy
            'interface'          — semua interface
            'bridge'             — bridge interface
            'dhcp-server'        — konfigurasi DHCP server
            'dhcp-network'       — network DHCP server
            'firewall-filter'    — firewall filter rules
            'firewall-nat'       — firewall NAT rules
            'vlan'               — VLAN interface
            'dns'                — konfigurasi DNS
            'ntp'                — konfigurasi NTP client
            'users'              — daftar user
            'ip-neighbor'        — perangkat direct connect (LLDP/CDP)
            'ip-neighbor-detail' — detail perangkat direct connect
            'ip-arp'             — ARP table
    """
    router_name = validate_router(router_name)
    entry = get_router_entries(router_name)[0]
    creds = ssh_creds_for(entry)
    ros = entry["ros_version"]
    section = section.strip().lower()

    _SECTION_MAP: dict[str, tuple[str, str]] = {
        "export":             ("/export",                            "export"),
        "ip-address":         ("/ip/address/print",                  "ip address print"),
        "ip-pool":            ("/ip/pool/print",                     "ip pool print"),
        "ip-route":           ("/ip/route/print",                    "ip route print"),
        "routing-static":     ("/ip/route/print where static",       "ip route print where static"),
        "routing-ospf":       ("/routing/ospf/instance/print",       "routing ospf instance print"),
        "routing-bgp":        ("/routing/bgp/connection/print",      "routing bgp instance print"),
        "routing-filter":     ("/routing/filter/rule/print",         "routing filter print"),
        "interface":          ("/interface/print",                   "interface print"),
        "bridge":             ("/interface/bridge/print",            "interface bridge print"),
        "dhcp-server":        ("/ip/dhcp-server/print",              "ip dhcp-server print"),
        "dhcp-network":       ("/ip/dhcp-server/network/print",      "ip dhcp-server network print"),
        "firewall-filter":    ("/ip/firewall/filter/print",          "ip firewall filter print"),
        "firewall-nat":       ("/ip/firewall/nat/print",             "ip firewall nat print"),
        "vlan":               ("/interface/vlan/print",              "interface vlan print"),
        "dns":                ("/ip/dns/print",                      "ip dns print"),
        "ntp":                ("/system/ntp/client/print",           "system ntp client print"),
        "users":              ("/user/print",                        "user print"),
        "ip-neighbor":        ("/ip/neighbor/print",                 "ip neighbor print"),
        "ip-arp":             ("/ip/arp/print",                      "ip arp print"),
        "ip-neighbor-detail": ("/ip/neighbor/print detail",          "ip neighbor print detail"),
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
    limit = 6000 if section == "export" else 4000
    if len(output) > limit:
        output = (
            output[:limit]
            + f"\n\n...[output terpotong, total {len(out)} karakter. "
            f"Gunakan section lebih spesifik untuk detail.]..."
        )
    return header + output
