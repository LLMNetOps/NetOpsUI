"""Mock fixtures for eval.py — semua tool returns fake but realistic data.

Setiap fixture adalah callable dengan signature yang sama dengan tool aslinya.
Digunakan oleh eval.py dalam mock mode untuk bypass koneksi SSH ke router.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Router inventory ──────────────────────────────────────────────────────────

_ROUTER_LIST = """Router yang tersedia:

  GATE-IDREN-UB  103.22.20.254    ROS v7  role=backbone  servers: —
  DTI            10.45.185.1      ROS v7  role=backbone  servers: DTI-server
  FIB            10.45.186.1      ROS v7  role=backbone  servers: FIB-server
  FH             10.45.187.1      ROS v7  role=backbone  servers: FH-server
  FEB            10.45.188.1      ROS v7  role=backbone  servers: FEB-server
  FIA            10.45.189.1      ROS v7  role=backbone  servers: FIA-server
  FP             10.45.190.1      ROS v7  role=backbone  servers: FP-server
  FAPET          10.45.191.1      ROS v7  role=backbone  servers: FAPET-server
  FT-DEKANAT     10.45.192.1      ROS v7  role=backbone  servers: FT-server
  FT-GBE         10.45.193.1      ROS v7  role=backbone  servers: FT-GBE-server
  FPIK           10.45.194.1      ROS v7  role=backbone  servers: FPIK-server
  FTP            10.45.195.1      ROS v7  role=backbone  servers: FTP-server
  FISIP          10.45.196.1      ROS v7  role=backbone  servers: FISIP-server
  FILKOM         10.45.197.1      ROS v7  role=backbone  servers: FILKOM-server
  VOKASI         10.45.198.1      ROS v7  role=backbone  servers: VOKASI-server
  FKG            10.45.199.1      ROS v7  role=backbone  servers: FKG-server
  FK-8           10.45.200.1      ROS v7  role=backbone  servers: FK-server
  FK-1           10.45.201.1      ROS v7  role=backbone  servers: FK-1-server"""

# ── Reachability ──────────────────────────────────────────────────────────────

_REACHABILITY_OK = {
    "GATE-IDREN-UB": "✓ GATE-IDREN-UB (103.22.20.254): reachable, ping 1.8ms",
    "DTI":           "✓ DTI (10.45.185.1): reachable, ping 2.1ms",
    "FIB":           "✓ FIB (10.45.186.1): reachable, ping 2.4ms",
    "FH":            "✓ FH (10.45.187.1): reachable, ping 2.6ms",
    "FEB":           "✓ FEB (10.45.188.1): reachable, ping 3.1ms",
    "FIA":           "✓ FIA (10.45.189.1): reachable, ping 2.9ms",
    "FP":            "✓ FP (10.45.190.1): reachable, ping 3.4ms",
    "FAPET":         "✓ FAPET (10.45.191.1): reachable, ping 2.8ms",
    "FT-DEKANAT":    "✓ FT-DEKANAT (10.45.192.1): reachable, ping 2.2ms",
    "FT-GBE":        "✓ FT-GBE (10.45.193.1): reachable, ping 2.5ms",
    "FPIK":          "✓ FPIK (10.45.194.1): reachable, ping 3.0ms",
    "FTP":           "✓ FTP (10.45.195.1): reachable, ping 2.7ms",
    "FISIP":         "✓ FISIP (10.45.196.1): reachable, ping 3.2ms",
    "FILKOM":        "✓ FILKOM (10.45.197.1): reachable, ping 2.3ms",
    "VOKASI":        "✓ VOKASI (10.45.198.1): reachable, ping 3.5ms",
    "FKG":           "✓ FKG (10.45.199.1): reachable, ping 2.0ms",
    "FK-8":          "✓ FK-8 (10.45.200.1): reachable, ping 2.8ms",
    "FK-1":          "✓ FK-1 (10.45.201.1): reachable, ping 2.1ms",
}

# Router yang sengaja down untuk skenario tertentu
_REACHABILITY_DOWN = {
    **_REACHABILITY_OK,
    "FTP": "✗ FTP (10.45.195.1): UNREACHABLE (timeout after 3s)",
    "FPIK": "✗ FPIK (10.45.194.1): UNREACHABLE (timeout after 3s)",
}

# ── BGP Sessions ──────────────────────────────────────────────────────────────

_BGP = {
    "GATE-IDREN-UB": """BGP Sessions — GATE-IDREN-UB (103.22.20.254)  Local AS: 23700
Total: 3  Established: 2  Down: 1
────────────────────────────────────────────────────────────────────────────────
  #  St    Type    RemAS  RemoteIP                  Uptime            Pfx  Name
────────────────────────────────────────────────────────────────────────────────
  1  ✓EST  ebgp    7713   103.22.20.1               14d02h15m         45000  IDREN-upstream
  2  ✓EST  ebgp    23710  10.45.0.2                 21d14h08m          1024  UB-transit
  3  ✗DWN  ebgp    45678  203.45.67.1               —                     0  backup-link

⚠ 1 session DOWN:
  - #3 backup-link  (remote: 203.45.67.1 AS45678)  last-stopped: 2d03h""",
}

# ── OSPF Neighbors ────────────────────────────────────────────────────────────

_OSPF = {
    "GATE-IDREN-UB": """OSPF Neighbors — GATE-IDREN-UB (103.22.20.254)
Total: 4  Full: 3  Masalah: 1
────────────────────────────────────────────────────────────────────────────────
  #  State     Address            RouterID           SC  Adjacency         Area
────────────────────────────────────────────────────────────────────────────────
  1  ✓Full     10.45.0.2          10.45.0.2           2  21d14h08m         0.0.0.0
  2  ✓Full     10.45.185.1        10.45.185.1         1  18d07h22m         0.0.0.0
  3  ✓Full     10.45.197.1        10.45.197.1         3  12d19h45m         0.0.0.0
  4  ⚠2Way     10.45.194.1        10.45.194.1        28  0d00h15m          0.0.0.0

⚠ Neighbor tidak FULL:
  - #4 10.45.194.1 (RouterID: 10.45.194.1) state=2Way state-changes=28 adjacency=0d00h15m

⚠ Neighbor Full tapi state-changes tinggi (>20) — riwayat instabilitas:
  - #4 10.45.194.1 (RouterID: 10.45.194.1) state-changes=28 adjacency=0d00h15m""",
}

# ── System Info ───────────────────────────────────────────────────────────────

def _make_system_info(router_name: str, cpu: int = 12, mem_total: int = 512,
                      mem_free: int = 280, uptime: str = "18d 07:22:15") -> str:
    hosts = {
        "GATE-IDREN-UB": "103.22.20.254", "DTI": "10.45.185.1",
        "FIB": "10.45.186.1", "FILKOM": "10.45.197.1", "FPIK": "10.45.194.1",
    }
    host = hosts.get(router_name, f"10.45.x.x")
    return (
        f"System Info — {router_name} ({host})\n"
        f"  Uptime    : {uptime}\n"
        f"  CPU Load  : {cpu}%\n"
        f"  Memory    : {mem_total - mem_free}/{mem_total} MB used "
        f"({int((mem_total - mem_free) / mem_total * 100)}%)\n"
        f"  ROS       : 7.14.3 (stable)\n"
        f"  Board     : CCR2004-1G-12S+2XS\n"
        f"  Voltage   : 24.0V\n"
        f"  Temp      : 38°C"
    )


_SYSTEM_INFO = {
    "GATE-IDREN-UB": _make_system_info("GATE-IDREN-UB", cpu=34, mem_total=1024, mem_free=620, uptime="21d 14:08:42"),
    "FPIK": _make_system_info("FPIK", cpu=89, mem_total=256, mem_free=18, uptime="0d 00:15:03"),
}

# ── Traffic Summary ───────────────────────────────────────────────────────────

_TRAFFIC: dict[str, str] = {
    "GATE-IDREN-UB": """Traffic Summary — GATE-IDREN-UB (103.22.20.254)
Interface       Rx          Tx          Rx-Drop   Tx-Drop
ether1          1.24 Gbps   0.87 Gbps   0         0
ether2          0.42 Gbps   0.61 Gbps   0         0
sfp1            0.08 Gbps   0.12 Gbps   12        0

Utilization tertinggi: ether1 (1.24 Gbps Rx, 0.87 Gbps Tx)
Capacity ether1: ~10 Gbps  →  utilization 12.4% Rx / 8.7% Tx""",
    "FILKOM": """Traffic Summary — FILKOM (10.45.197.1)
Interface       Rx          Tx          Rx-Drop   Tx-Drop
ether1          0.78 Gbps   0.54 Gbps   0         0
ether2          0.31 Gbps   0.28 Gbps   0         2
bridge-lan      0.78 Gbps   0.54 Gbps   0         0

Utilization tertinggi: ether1 (0.78 Gbps Rx)
Capacity ether1: ~1 Gbps  →  utilization 78% Rx / 54% Tx  ⚠ mendekati jenuh""",
}

# ── DHCP Audit ────────────────────────────────────────────────────────────────

_DHCP_AUDIT_NORMAL = """DHCP Audit — semua router
─────────────────────────────────────────────────────────────────────
Router          Pool            Total   Used  Free  Util%
─────────────────────────────────────────────────────────────────────
DTI             10.45.185.0/24   253    124   129   49%
FIB             10.45.186.0/24   253    198   55    78%
FH              10.45.187.0/24   253    89    164   35%
FEB             10.45.188.0/24   253    231   22    91%  ⚠ hampir penuh
FIA             10.45.189.0/24   253    145   108   57%
FP              10.45.190.0/24   253    67    186   26%
FAPET           10.45.191.0/24   253    112   141   44%
FT-DEKANAT      10.45.192.0/24   253    178   75    70%
FT-GBE          10.45.193.0/24   253    201   52    79%
FPIK            10.45.194.0/24   253    43    210   17%
FTP             10.45.195.0/24   253    88    165   35%
FISIP           10.45.196.0/24   253    167   86    66%
FILKOM          10.45.197.0/24   253    244   9     96%  ⚠ KRITIS
VOKASI          10.45.198.0/24   253    134   119   53%
FKG             10.45.199.0/24   253    56    197   22%
FK-8            10.45.200.0/24   253    189   64    75%
FK-1            10.45.201.0/24   253    211   42    83%

⚠ Pool hampir penuh (>90%): FEB (91%), FILKOM (96%)
Rekomendasi: perluas subnet FILKOM ke /23 (510 host) segera."""

_DHCP_AUDIT_EXHAUSTION = """DHCP Audit — semua router
─────────────────────────────────────────────────────────────────────
Router          Pool            Total   Used  Free  Util%
─────────────────────────────────────────────────────────────────────
DTI             10.45.185.0/24   253    124   129   49%
FIB             10.45.186.0/24   253    198   55    78%
FH              10.45.187.0/24   253    89    164   35%
FEB             10.45.188.0/24   253    250   3     99%  ⚠ KRITIS
FIA             10.45.189.0/24   253    145   108   57%
FP              10.45.190.0/24   253    67    186   26%
FAPET           10.45.191.0/24   253    112   141   44%
FT-DEKANAT      10.45.192.0/24   253    178   75    70%
FT-GBE          10.45.193.0/24   253    201   52    79%
FPIK            10.45.194.0/24   253    43    210   17%
FTP             10.45.195.0/24   253    88    165   35%
FISIP           10.45.196.0/24   253    167   86    66%
FILKOM          10.45.197.0/24   253    253   0     100% ⚠ HABIS
VOKASI          10.45.198.0/24   253    134   119   53%
FKG             10.45.199.0/24   253    56    197   22%
FK-8            10.45.200.0/24   253    189   64    75%
FK-1            10.45.201.0/24   253    211   42    83%

⚠ Pool HABIS: FILKOM (253/253, 0 free) — perangkat baru tidak dapat IP
⚠ Pool KRITIS: FEB (250/253, 3 free)
Rekomendasi: FILKOM → perluas ke /23 SEGERA. FEB → perluas ke /23."""

# ── Security Audit ────────────────────────────────────────────────────────────

_SECURITY: dict[str, str] = {
    "GATE-IDREN-UB": """Security Audit — GATE-IDREN-UB (103.22.20.254)
Firewall Rules  : 48 rules aktif
SSH Access      : enabled (port 22)
Winbox          : disabled ✓
API             : disabled ✓
Telnet          : disabled ✓
FTP             : disabled ✓
Default creds   : changed ✓

Recent Auth Failures (30 menit terakhir):
  Tidak ada login failure terdeteksi.

Open ports (TCP): 22, 179 (BGP)
Rekomendasi: tidak ada temuan kritis.""",

    "all": """Security Audit — semua router
─────────────────────────────────────────────────────────────────────
Router          SSH  Winbox  API  Telnet  Firewall  Auth-Fail (1h)
─────────────────────────────────────────────────────────────────────
GATE-IDREN-UB   ✓    ✗       ✗    ✗       48 rules   0
DTI             ✓    ✓ ⚠     ✗    ✗       32 rules   0
FIB             ✓    ✗       ✗    ✗       28 rules   0
FH              ✓    ✓ ⚠     ✗    ✗       25 rules   0
FEB             ✓    ✗       ✗    ✗       30 rules   847  ⚠ BRUTE FORCE
FIA             ✓    ✗       ✗    ✗       27 rules   0
FP              ✓    ✗       ✗    ✗       24 rules   0
FAPET           ✓    ✓ ⚠     ✗    ✗       22 rules   0
FT-DEKANAT      ✓    ✗       ✗    ✗       31 rules   0
FT-GBE          ✓    ✗       ✗    ✗       29 rules   12
FISIP           ✓    ✗       ✗    ✗       26 rules   0
FILKOM          ✓    ✗       ✗    ✗       35 rules   0
VOKASI          ✓    ✓ ⚠     ✗    ✗       20 rules   3
FKG             ✓    ✗       ✗    ✗       23 rules   0
FK-8            ✓    ✗       ✗    ✗       28 rules   0
FK-1            ✓    ✗       ✗    ✗       26 rules   0

⚠ Temuan kritis:
  - FEB: 847 SSH auth failures dalam 1 jam terakhir — kemungkinan brute force aktif
    IP penyerang terdeteksi: 185.220.101.47, 185.220.101.48, 193.106.31.45
  - DTI, FH, FAPET, VOKASI: Winbox masih aktif — risiko eksploitasi protokol MikroTik""",

    "FEB": """Security Audit — FEB (10.45.188.1)
Firewall Rules  : 30 rules aktif
SSH Access      : enabled (port 22)
Winbox          : disabled ✓
API             : disabled ✓
Telnet          : disabled ✓

Recent Auth Failures (1 jam terakhir): 847 failures
Top attacker IPs:
  185.220.101.47  →  412 attempts
  185.220.101.48  →  298 attempts
  193.106.31.45   →  137 attempts

⚠ BRUTE FORCE AKTIF — segera blokir IP penyerang""",
}

# ── Router Log ────────────────────────────────────────────────────────────────

_LOG: dict[tuple[str, str], str] = {
    ("FEB", ""):
        """Log — FEB (10.45.188.1) [30 baris terakhir]
2026-05-09 14:22:01 system,error,critical login failure for user admin from 185.220.101.47
2026-05-09 14:22:02 system,error,critical login failure for user admin from 185.220.101.47
2026-05-09 14:22:04 system,error,critical login failure for user admin from 185.220.101.48
2026-05-09 14:22:05 system,error,critical login failure for user admin from 185.220.101.47
2026-05-09 14:22:07 system,error,critical login failure for user root from 185.220.101.48
2026-05-09 14:22:08 system,error,critical login failure for user admin from 193.106.31.45
2026-05-09 14:22:09 system,error,critical login failure for user admin from 185.220.101.47
2026-05-09 14:22:11 system,error,critical login failure for user admin from 185.220.101.48
2026-05-09 14:22:13 firewall,info rule #12 drop src=185.220.101.47 proto=tcp dst-port=22
2026-05-09 14:22:14 system,error,critical login failure for user admin from 193.106.31.45""",

    ("FPIK", "interface"):
        """Log — FPIK (10.45.194.1) topic=interface [30 baris terakhir]
2026-05-09 14:01:02 interface,warning ether2 link down
2026-05-09 14:01:07 interface,warning ether2 link up
2026-05-09 14:01:09 interface,warning ether2 link down
2026-05-09 14:01:15 interface,warning ether2 link up
2026-05-09 14:01:18 interface,warning ether2 link down
2026-05-09 14:01:24 interface,warning ether2 link up
2026-05-09 14:01:27 interface,warning ether2 link down
2026-05-09 14:03:52 interface,warning ether2 link up
2026-05-09 14:04:01 interface,warning ether2 link down
2026-05-09 14:05:30 interface,warning ether2 link up
2026-05-09 14:05:35 interface,warning ether2 link down
Pola: ether2 flapping 11x dalam 5 menit, rata-rata setiap 28 detik""",

    ("GATE-IDREN-UB", ""):
        """Log — GATE-IDREN-UB (103.22.20.254) [30 baris terakhir]
2026-05-09 14:20:01 bgp,info session backup-link state changed Active -> Connect
2026-05-09 14:20:05 bgp,info session backup-link state changed Connect -> Active
2026-05-09 14:18:30 ospf,info neighbor 10.45.194.1 state changed Full -> 2Way
2026-05-09 14:18:30 ospf,info neighbor 10.45.194.1 DR election
2026-05-09 14:18:31 ospf,info neighbor 10.45.194.1 state changed 2Way -> ExStart
2026-05-09 14:18:32 ospf,info neighbor 10.45.194.1 state changed ExStart -> 2Way""",
}

# ── Interface Stats ───────────────────────────────────────────────────────────

_INTERFACE: dict[str, str] = {
    "FPIK": """Interface Stats — FPIK (10.45.194.1)
Interface   Status   Rx-Bytes       Tx-Bytes       Rx-Err  Tx-Err  Rx-Drop  Tx-Drop
ether1      up       1.2 GB         0.8 GB         0       0       0        0
ether2      up       0.4 GB         0.3 GB         1842    0       924      0        ⚠
ether3      down     —              —              —       —       —        —
bridge-lan  up       1.4 GB         0.9 GB         0       0       0        0

⚠ ether2: Rx-Error=1842, Rx-Drop=924 — indikasi link fisik bermasalah""",

    "GATE-IDREN-UB": """Interface Stats — GATE-IDREN-UB (103.22.20.254)
Interface   Status   Rx-Bytes       Tx-Bytes       Rx-Err  Tx-Err  Rx-Drop  Tx-Drop
ether1      up       12.4 GB        8.7 GB         0       0       0        0
ether2      up       4.2 GB         6.1 GB         0       0       0        0
sfp1        up       0.8 GB         1.2 GB         12      0       0        0
sfp2        down     —              —              —       —       —        —

⚠ sfp1: Rx-Error=12 (minor)""",
}

# ── Write Document (real write, temp path) ────────────────────────────────────

_MOCK_DOC_DIR = Path(__file__).parent.parent.parent / "data" / "test-output"


def mock_write_document(filename: str, content: str) -> str:
    _MOCK_DOC_DIR.mkdir(parents=True, exist_ok=True)
    path = _MOCK_DOC_DIR / filename
    path.write_text(content, encoding="utf-8")
    return f"Dokumen berhasil disimpan: {path}"


# ── Fixture map: tool_name → callable ────────────────────────────────────────

def _reachability_normal(router_name: str) -> str:
    return _REACHABILITY_OK.get(router_name, f"✓ {router_name}: reachable, ping 2.5ms")


def _reachability_with_down(router_name: str) -> str:
    return _REACHABILITY_DOWN.get(router_name, f"✓ {router_name}: reachable, ping 2.5ms")


def _system_info(router_name: str) -> str:
    return _SYSTEM_INFO.get(router_name, _make_system_info(router_name))


def _bgp(router_name: str) -> str:
    return _BGP.get(router_name, f"Tidak ada BGP session di {router_name}.")


def _ospf(router_name: str) -> str:
    return _OSPF.get(router_name, f"Tidak ada OSPF neighbor di {router_name}.")


def _traffic(router_name: str) -> str:
    return _TRAFFIC.get(router_name, f"Tidak ada data traffic untuk {router_name}.")


def _security(router_name: str = "all") -> str:
    return _SECURITY.get(router_name, _SECURITY["GATE-IDREN-UB"])


def _router_log(router_name: str, topic: str = "", lines: int = 30) -> str:
    key = (router_name, topic)
    if key in _LOG:
        return _LOG[key]
    key_no_topic = (router_name, "")
    if key_no_topic in _LOG:
        return _LOG[key_no_topic]
    return f"Log — {router_name}: tidak ada entri log yang relevan."


def _interface_stats(router_name: str) -> str:
    return _INTERFACE.get(router_name, f"Interface stats {router_name}: semua interface normal, tidak ada error.")


def _dhcp_normal() -> str:
    return _DHCP_AUDIT_NORMAL


def _dhcp_exhaustion() -> str:
    return _DHCP_AUDIT_EXHAUSTION


def _current_time() -> str:
    WIB = timezone(timedelta(hours=7))
    now = datetime(2026, 5, 9, 14, 22, 0, tzinfo=WIB)
    return (
        f"Waktu saat ini (WIB):\n"
        f"  Hari    : Sabtu\n"
        f"  Tanggal : 09 Mei 2026\n"
        f"  Jam     : 14:22:00 WIB\n"
        f"  ISO     : {now.isoformat()}"
    )


# ── Named fixture sets untuk scenario ────────────────────────────────────────

# ── Router list dengan gate_idren role (untuk scope test) ─────────────────────

_ROUTER_LIST_WITH_IDREN = """Router yang tersedia:

  GATE-IDREN-UB  103.22.20.254    ROS v7  role=gate_idren  servers: —
  GATE-IDREN-UI  103.22.21.254    ROS v7  role=gate_idren  servers: —
  DTI            10.45.185.1      ROS v7  role=backbone    servers: DTI-server
  FIB            10.45.186.1      ROS v7  role=backbone    servers: FIB-server
  FH             10.45.187.1      ROS v7  role=backbone    servers: FH-server
  FEB            10.45.188.1      ROS v7  role=backbone    servers: FEB-server
  FILKOM         10.45.197.1      ROS v7  role=backbone    servers: FILKOM-server"""

# ── BGP primary session DOWN (trigger validasi scenario) ─────────────────────

_BGP_PRIMARY_DOWN = {
    "GATE-IDREN-UB": """BGP Sessions — GATE-IDREN-UB (103.22.20.254)  Local AS: 23700
Total: 2  Established: 1  Down: 1
────────────────────────────────────────────────────────────────────────────────
  #  St    Type    RemAS  RemoteIP                  Uptime            Pfx  Name
────────────────────────────────────────────────────────────────────────────────
  1  ✗DWN  ebgp    7713   103.22.20.1               —                     0  IDREN-upstream
  2  ✓EST  ebgp    23710  10.45.0.2                 21d14h08m          1024  UB-transit

✗ 1 session DOWN (primary uplink):
  - #1 IDREN-upstream  (remote: 103.22.20.1 AS7713)  last-stopped: 0d00h45m
  Dampak: konektivitas ke jaringan IDREN nasional TERPUTUS selama 45 menit.""",
}

_BGP_PRIMARY_NOW_UP = {
    "GATE-IDREN-UB": """BGP Sessions — GATE-IDREN-UB (103.22.20.254)  Local AS: 23700
Total: 2  Established: 2  Down: 0
────────────────────────────────────────────────────────────────────────────────
  #  St    Type    RemAS  RemoteIP                  Uptime            Pfx  Name
────────────────────────────────────────────────────────────────────────────────
  1  ✓EST  ebgp    7713   103.22.20.1               0d00h03m          45000  IDREN-upstream
  2  ✓EST  ebgp    23710  10.45.0.2                 21d14h08m          1024  UB-transit

✓ Semua session established.""",
}

# ── Security with SEGERA format ───────────────────────────────────────────────

_SECURITY_WITH_SEGERA = {
    **_SECURITY,
    "FEB": """Security Audit — FEB (10.45.188.1)
Firewall Rules  : 30 rules aktif
SSH             : enabled (port 22)
Winbox          : disabled ✓
Telnet          : disabled ✓

Recent Auth Failures (1 jam terakhir): 847 failures
Top attacker IPs:
  185.220.101.47  →  412 attempts  (burst pattern = credential stuffing otomatis)
  185.220.101.48  →  298 attempts
  193.106.31.45   →  137 attempts

🚨 **SEGERA** — Serangan brute force aktif dari 3 IP: blokir segera di firewall FEB.
Perintah: /ip/firewall/address-list/add list=blacklist address=185.220.101.47""",
}

# ── NetBox mock data ──────────────────────────────────────────────────────────

_NETBOX_DEVICES = """Device di NetBox [idren] (29 total)
────────────────────────────────────────────────────────────
  GATE-IDREN-UB    primary_ip=103.78.233.1/32  status=Active  site=Universitas Brawijaya - UB
  GATE-IDREN-ITS   primary_ip=—                status=Planned  site=Institut Teknologi Sepuluh Nopember - ITS
  GATE-IDREN-UI    primary_ip=—                status=Planned  site=Universitas Indonesia - UI
  GATE-IDREN-UGM   primary_ip=—                status=Active   site=Universitas Gadjah Mada - UGM
  GATE-IDREN-UNDIP primary_ip=—                status=Active   site=Universitas Diponegoro UNDIP
  GATE-IDREN-UNUD  primary_ip=—                status=Active   site=Universitas Udayana UNUD
  (... 23 device lain)

Total: 29 device"""

# Semua 39 VLAN interface GATE-IDREN-UB sudah ada di NetBox.
# Tag managed-by-agent belum diterapkan — tool fallback tampilkan semua.
_NETBOX_INTERFACES = {
    "GATE-IDREN-UB": """Interface 'GATE-IDREN-UB' [semua virtual — tag 'managed-by-agent' belum diterapkan] (41 interface)
────────────────────────────────────────────────────────────

  VLAN-702-CBN-GATE-IDREN-UB-NODE-IDREN-PPNS
    vlan-id=702  parent=qsfp28-1-1  enabled
    desc=TO NODE-IDREN-PPNS VIA CBN
    IPs: 172.17.0.45/30

  vlan906-GATE-ARENAPAC
    vlan-id=906  parent=qsfp28-2-1  enabled
    desc=TO GATE-ARENAPAC VIA FIBER
    IPs: 103.161.244.202/29

  vlan2002-TO-GATE-IDREN-ITS-VIA-TELKOM
    vlan-id=2002  parent=qsfp28-1-1  enabled
    desc=TO GATE-IDREN-ITS VIA TELKOM
    IPs: 172.31.0.21/30

  vlan2006-TO-NODE-IDREN-UNPATTI-VIA-TELKOM
    vlan-id=2006  parent=qsfp28-1-1  enabled
    desc=TO NODE-IDREN-UNPATTI VIA TELKOM
    IPs: 172.17.0.4/31

  vlan2009-TO-GATE-UNEJ-VIA-TELKOM
    vlan-id=2009  parent=qsfp28-1-1  enabled
    desc=TO GATE-IDREN-UNEJ VIA TELKOM
    IPs: 103.241.204.217/31, 172.17.0.16/31

  vlan2014-TO-NODE-UNSRAT-VIA-TELKOM
    vlan-id=2014  parent=qsfp28-1-1  enabled
    desc=TO NODE-IDREN-UNSRAT VIA TELKOM
    IPs: 172.17.0.33/30

  (... 35 interface lain)""",
}

_NETBOX_IPS = {
    "GATE-IDREN-UB": """IP Address di NetBox — GATE-IDREN-UB (46 total):

  172.17.0.45/30   interface=VLAN-702-CBN-GATE-IDREN-UB-NODE-IDREN-PPNS  (TO NODE-IDREN-PPNS VIA CBN)
  103.161.244.202/29 interface=vlan906-GATE-ARENAPAC  (TO GATE-ARENAPAC VIA FIBER)
  172.31.0.21/30   interface=vlan2002-TO-GATE-IDREN-ITS-VIA-TELKOM
  172.17.0.4/31    interface=vlan2006-TO-NODE-IDREN-UNPATTI-VIA-TELKOM
  172.17.0.16/31   interface=vlan2009-TO-GATE-UNEJ-VIA-TELKOM
  103.241.204.217/31 interface=vlan2009-TO-GATE-UNEJ-VIA-TELKOM
  172.17.0.33/30   interface=vlan2014-TO-NODE-UNSRAT-VIA-TELKOM
  103.78.233.1/32  interface=lo0
  (... 38 IP lain)

Total: 46 IP address""",
}

# Drift real: semua 39 VLAN interface cocok. Ada 2 IP prefix mismatch (NetBox /31, router /32).
_NETBOX_DRIFT = {
    "GATE-IDREN-UB": """Drift Report: GATE-IDREN-UB (172.18.4.220) ↔ NetBox 'GATE-IDREN-UB'
══════════════════════════════════════════════════════════════════════

[!] Tag 'managed-by-agent' belum ada — membandingkan semua virtual interface

[INTERFACE VLAN] NetBox: 39  |  Router: 39
  Semua VLAN interface NetBox sudah ada di router (by VLAN ID). ✓

[IP ADDRESS] NetBox: 46  |  Router: 47

  IP PERLU DITAMBAH DI ROUTER (2):
    + 172.17.0.16/31  interface=vlan2009-TO-GATE-UNEJ-VIA-TELKOM
      → /ip/address/add address=172.17.0.16/31 interface=vlan2009-TO-GATE-UNEJ-VIA-TELKOM
    + 172.17.0.4/31  interface=vlan2006-TO-NODE-IDREN-UNPATTI-VIA-TELKOM
      → /ip/address/add address=172.17.0.4/31 interface=vlan2006-TO-NODE-IDREN-UNPATTI-VIA-TELKOM

  IP ADA DI ROUTER, TIDAK DI NETBOX (3) [informasi]:
    ? 172.17.0.16/32  interface=vlan2009-TO-GATE-UNEJ-VIA-TELKOM
    ? 172.17.0.4/32  interface=vlan2006-TO-NODE-IDREN-UNPATTI-VIA-TELKOM
    ? 192.168.251.1/32  interface=wireguard1-mkt-ai3

══════════════════════════════════════════════════════════════════════
HASIL: 2 item perlu disinkronisasi ke router (0 interface, 2 IP).
Handoff ke config_agent untuk eksekusi dengan approval operator.""",
}

_NETBOX_BGP_DRIFT = """BGP Drift — NetBox vs Router  [IDREN]
══════════════════════════════════════════════════════════════════════

── GATE-IDREN-UB (103.78.233.1) ──
  ⚠ Di router, tidak di NetBox (3):
    - TO-GATE-IDREN-ITS-VIA-TELKOM  AS23711  ✓  (remote: 172.31.0.22)
    - TO-GATE-IDREN-UNUD-VIA-TELKOM AS23720  ✓  (remote: 172.31.0.10)
    - TO-GATE-ARENAPAC              AS55818  ✓  (remote: 103.161.244.201)
  ✓ Di kedua sumber (2): TO-IDREN-UPSTREAM, TO-GATE-IDREN-UI  cocok.

── GATE-IDREN-ITS (172.31.0.22) ──
  ✓ Sinkron — 4 session cocok.

══════════════════════════════════════════════════════════════════════
Ada drift. Jalankan populate_netbox_bgp() untuk sinkronisasi."""

_NETBOX_BGP_POPULATE = """Populate NetBox BGP — GATE-IDREN-UB [EKSEKUSI]
══════════════════════════════════════════════════════════════════════

  [auto-create ASN] AS23720
  [auto-create ASN] AS55818
  ✓ TO-GATE-IDREN-ITS-VIA-TELKOM  — created (remote: 172.31.0.22 AS23711)
  ✓ TO-GATE-IDREN-UNUD-VIA-TELKOM — created (remote: 172.31.0.10 AS23720)
  ✓ TO-GATE-ARENAPAC              — created (remote: 103.161.244.201 AS55818)

Selesai: 3 session ditambahkan ke NetBox."""

# Router punya 35 VLAN interface, NetBox baru dokumentasikan 4.
# Dry-run menampilkan 31 interface yang belum terdokumentasi.
_NETBOX_POPULATE_FROM_ROUTER_DRY = """Populate NetBox dari Router: GATE-IDREN-UB → 'GATE-IDREN-UB' [DRY-RUN]
══════════════════════════════════════════════════════════════════════

[FIX PARENT] 0 interface perlu diperbaiki:
  Tidak ada.

[INTERFACE BARU] 0 VLAN interface akan dibuat:
  Tidak ada. Semua 39 VLAN interface router sudah terdokumentasi di NetBox.

[IP BARU] 1 IP address akan ditambah:
  192.168.251.1/32  interface=wireguard1-mkt-ai3

[KONFLIK PREFIX] 2 IP perlu verifikasi manual:
  Router: 172.17.0.16/32  NetBox: 172.17.0.16/31  interface=vlan2009-TO-GATE-UNEJ-VIA-TELKOM
  Router: 172.17.0.4/32   NetBox: 172.17.0.4/31   interface=vlan2006-TO-NODE-IDREN-UNPATTI-VIA-TELKOM
  → Tidak diubah otomatis. Periksa prefix yang benar dan update manual di NetBox.

══════════════════════════════════════════════════════════════════════
DRY-RUN selesai. Untuk eksekusi, jalankan ulang dengan dry_run=False."""

_NETBOX_VLAN_GROUPS = """VLAN Groups di NetBox [IDREN]:

  vg-indosat   range=551-600   active=7   reserved=0   kosong=43
  vg-moratel   range=601-650   active=4   reserved=0   kosong=46
  vg-cbn       range=701-760   active=3   reserved=0   kosong=57
  vg-iforte    range=1101-1110 active=4   reserved=0   kosong=6
  vg-hsp       range=1051-1060 active=2   reserved=0   kosong=8
  vg-telkom    range=2001-2050 active=15  reserved=0   kosong=35
  vg-mgmt      range=2-100     active=5   reserved=0   kosong=94

Total: 7 VLAN group"""

_NETBOX_NEXT_VLAN = {
    "vg-indosat": "VLAN berikutnya tersedia di group 'vg-indosat': ID=558 (slot kosong)",
    "vg-moratel": "VLAN berikutnya tersedia di group 'vg-moratel': ID=604 (slot kosong)",
    "vg-cbn":     "VLAN berikutnya tersedia di group 'vg-cbn': ID=704 (slot kosong)",
    "vg-telkom":  "VLAN berikutnya tersedia di group 'vg-telkom': ID=2016 (slot kosong)",
}

_NETBOX_VLAN_GROUP_DETAIL = {
    "vg-telkom": """Detail VLAN Group: vg-telkom (range 2001-2050)

  Active (15):  2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                2012, 2014, 2015, 2016, 2020, 2025
  Reserved (0): (tidak ada)
  Kosong (35):  2010-2011, 2013, 2017-2019, 2021-2024, 2026-2050""",
    "vg-indosat": """Detail VLAN Group: vg-indosat (range 551-600)

  Active (7):   551, 552, 553, 554, 555, 556, 557
  Reserved (0): (tidak ada)
  Kosong (43):  558-600""",
}


def _netbox_devices(instance: str = "idren") -> str:
    return _NETBOX_DEVICES


def _netbox_interfaces(device_name: str, instance: str = "auto") -> str:
    return _NETBOX_INTERFACES.get(device_name, f"Tidak ada interface managed untuk '{device_name}'.")


def _netbox_ips(device_name: str, instance: str = "auto") -> str:
    return _NETBOX_IPS.get(device_name, f"Tidak ada IP address di NetBox untuk '{device_name}'.")


def _netbox_drift(router_name: str, device_name: str = "", instance: str = "auto") -> str:
    return _NETBOX_DRIFT.get(router_name, f"Tidak ada drift data untuk '{router_name}'.")


def _netbox_bgp_drift(router_name: str = "", instance: str = "idren") -> str:
    return _NETBOX_BGP_DRIFT


def _netbox_bgp_populate(router_name: str = "", instance: str = "idren") -> str:
    return _NETBOX_BGP_POPULATE


def _netbox_populate_from_router(router_name: str, device_name: str = "", dry_run: bool = True, instance: str = "auto") -> str:
    return _NETBOX_POPULATE_FROM_ROUTER_DRY


def _netbox_vlan_groups(instance: str = "idren") -> str:
    return _NETBOX_VLAN_GROUPS


def _netbox_next_vlan(group_slug: str, instance: str = "idren") -> str:
    return _NETBOX_NEXT_VLAN.get(group_slug, f"Group '{group_slug}' tidak ditemukan.")


def _netbox_vlan_group_detail(group_slug: str, instance: str = "idren") -> str:
    return _NETBOX_VLAN_GROUP_DETAIL.get(group_slug, f"Detail group '{group_slug}' tidak ditemukan.")


def _netbox_create_vlan(device_name: str, vlan_id: int, parent_interface: str, description: str = "", instance: str = "idren") -> str:
    return f"✓ Interface vlan{vlan_id} berhasil dibuat di NetBox untuk '{device_name}' (parent={parent_interface})."


def _netbox_add_ip(ip_with_prefix: str, interface_name: str, device_name: str, description: str = "", instance: str = "auto") -> str:
    return f"✓ IP {ip_with_prefix} berhasil ditambahkan ke NetBox (interface={interface_name}, device={device_name})."


def _netbox_update_interface(device_name: str, interface_name: str, instance: str = "auto", **kwargs) -> str:
    return f"✓ Interface '{interface_name}' di '{device_name}' berhasil diupdate di NetBox."


def _resolve_router_host(router_name: str) -> str:
    hosts = {"GATE-IDREN-UB": "103.22.20.254", "GATE-IDREN-ITS": "103.25.10.1"}
    ip = hosts.get(router_name.upper(), "10.0.0.1")
    return f"Router '{router_name}' → host={ip}"


# ── Named fixture sets untuk scenario ────────────────────────────────────────

FIXTURE_SETS: dict[str, dict[str, object]] = {
    "default": {
        "list_routers": lambda: _ROUTER_LIST,
        "get_current_time": _current_time,
        "check_reachability": _reachability_normal,
        "get_system_info": _system_info,
        "get_bgp_sessions": _bgp,
        "get_ospf_neighbors": _ospf,
        "get_traffic_summary": _traffic,
        "get_interface_stats": _interface_stats,
        "audit_dhcp": _dhcp_normal,
        "audit_security": _security,
        "get_router_log": _router_log,
        "write_document": mock_write_document,
        "backup_router_config": lambda router_name: f"Backup {router_name} berhasil: backups/{router_name}-20260509.rsc",
        "list_backups": lambda router_name: f"Backup tersedia untuk {router_name}:\n  backups/{router_name}-20260509.rsc (1.2 KB)\n  backups/{router_name}-20260508.rsc (1.1 KB)",
        "get_router_config": lambda router_name, section="export": f"# Router config {router_name} — section {section}\n/ip address\nadd address=10.45.x.1/24 interface=ether1",
        "run_command": lambda router_name, command: f"Output {command} di {router_name}:\n(ok)",
        "run_command_all": lambda command: f"Output '{command}' di semua router:\n(ok — 17 router)",
        "get_dhcp_leases": lambda router_name, dhcp_server="": f"DHCP Leases {router_name}: 150 active leases",
        "search_device": lambda query: f"Perangkat ditemukan: {query} → MAC aa:bb:cc:dd:ee:ff IP 10.45.185.42 router DTI",
        "check_ssh_access": lambda router_name: f"✓ {router_name}: SSH accessible",
        "run_diagnostic": lambda router_name: f"Diagnostic {router_name}: semua sistem normal",
        "list_templates": lambda: "Template tersedia:\n  network-status.md\n  routing-bgp-ospf.md",
        "read_template": lambda name: f"# Template: {name}\n[konten template]",
        "list_reports": lambda: "Laporan tersedia:\n  laporan/network-status-20260509.md",
        "get_report": lambda filename: f"# Laporan\n[konten laporan {filename}]",
        "fetch_url": lambda url: f"Konten dari {url}:\n[mock content]",
        "write_skill": lambda domain, name, content: f"Skill {name} berhasil disimpan di skills/{domain}/{name}.md",
        # NetBox tools — default fixture (data kosong/netral)
        "get_netbox_devices": _netbox_devices,
        "get_netbox_device_interfaces": _netbox_interfaces,
        "get_netbox_device_ips": _netbox_ips,
        "get_netbox_drift_report": _netbox_drift,
        "get_netbox_bgp_drift": _netbox_bgp_drift,
        "populate_netbox_bgp": _netbox_bgp_populate,
        "populate_netbox_from_router": _netbox_populate_from_router,
        "get_netbox_vlan_groups": _netbox_vlan_groups,
        "get_next_available_vlan": _netbox_next_vlan,
        "get_netbox_vlan_group_detail": _netbox_vlan_group_detail,
        "create_netbox_vlan_interface": _netbox_create_vlan,
        "add_netbox_ip_address": _netbox_add_ip,
        "update_netbox_interface": _netbox_update_interface,
        "resolve_router_host": _resolve_router_host,
        "patch_router_host": lambda router_name, host, **kw: f"✓ Host router '{router_name}' diupdate → {host}",
        "remember_router_fact": lambda router_name, fact_type, value, source="": f"✓ Fact disimpan: {router_name}.{fact_type}={value}",
        "recall_router_facts": lambda router_name: f"Facts untuk '{router_name}': (tidak ada data tersimpan)",
    },
    "dhcp_exhaustion": {
        "audit_dhcp": _dhcp_exhaustion,
    },
    "brute_force": {
        "audit_security": _security,
        "get_router_log": _router_log,
    },
    "interface_flapping": {
        "check_reachability": _reachability_with_down,
        "get_interface_stats": _interface_stats,
        "get_router_log": _router_log,
        "get_system_info": lambda router_name: _SYSTEM_INFO.get(
            router_name, _make_system_info(router_name, cpu=89 if router_name == "FPIK" else 12)
        ),
    },
    # Validasi flow: BGP primary DOWN → monitor triggers wati → wati konfirmasi masih down → config
    "validasi_bgp_down": {
        "list_routers": lambda: _ROUTER_LIST_WITH_IDREN,
        "get_bgp_sessions": lambda router_name: _BGP_PRIMARY_DOWN.get(
            router_name, f"Tidak ada BGP session di {router_name}."
        ),
        "get_ospf_neighbors": _ospf,
        "check_reachability": _reachability_normal,
        "check_ssh_access": lambda router_name: f"✓ {router_name}: SSH accessible",
        "get_interface_stats": _interface_stats,
    },
    # Validasi resolved: BGP DOWN saat monitor, tapi sudah UP saat wati verifikasi
    "validasi_bgp_resolved": {
        "list_routers": lambda: _ROUTER_LIST_WITH_IDREN,
        "get_bgp_sessions": lambda router_name: _BGP_PRIMARY_NOW_UP.get(
            router_name, f"Tidak ada BGP session di {router_name}."
        ),
        "check_reachability": _reachability_normal,
        "check_ssh_access": lambda router_name: f"✓ {router_name}: SSH accessible",
    },
    # Scope test: hanya router gate_idren yang diperiksa
    "scope_idren": {
        "list_routers": lambda: _ROUTER_LIST_WITH_IDREN,
        "check_reachability": _reachability_normal,
        "get_system_info": _system_info,
    },
    # Security brute force dengan action items SEGERA (trigger validasi)
    "security_brute_force_segera": {
        "audit_security": lambda router_name="all": _SECURITY_WITH_SEGERA.get(
            router_name, _SECURITY.get(router_name, _SECURITY["GATE-IDREN-UB"])
        ),
        "get_router_log": _router_log,
        "check_reachability": _reachability_normal,
        "get_bgp_sessions": _bgp,
        "get_system_info": _system_info,
    },
}


def get_fixture_set(name: str) -> dict[str, object]:
    """Gabungkan fixture set 'default' dengan overlay set yang diminta."""
    base = dict(FIXTURE_SETS["default"])
    if name != "default" and name in FIXTURE_SETS:
        base.update(FIXTURE_SETS[name])
    return base
