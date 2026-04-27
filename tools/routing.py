"""Tools: routing table, OSPF, BGP — read-only."""

from __future__ import annotations

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_run_command


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
    creds = ssh_creds()
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
            if len(output) > 800:
                output = output[:800] + f"\n  ...[+{len(out)-800} karakter]"
            lines.append(output)
            has_any = True

    if not has_any:
        lines.append("\nTidak ada konfigurasi routing ditemukan di router ini.")
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
    creds = ssh_creds()
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
