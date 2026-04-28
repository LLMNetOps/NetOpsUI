"""Tool: cek reachability router via ICMP ping lokal dan TCP/SSH diagnostics."""

from __future__ import annotations

import re
import socket
import subprocess

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries


@tool
def check_reachability(router_name: str) -> str:
    """
    Cek apakah router dapat dijangkau via ping dari host lokal.
    Args:
        router_name: Nama router (contoh: DTI, FIB, FILKOM).
                     Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    hosts = list({e["host"] for e in get_router_entries(router_name)})
    results = []
    for host in hosts:
        try:
            res = subprocess.run(
                ["ping", "-c", "1", "-W", "3", host],
                capture_output=True,
                text=True,
                timeout=5,
            )
            reachable = res.returncode == 0
            rtt = "-"
            m = re.search(r"time=([\d.]+)", res.stdout)
            if m:
                rtt = f"{m.group(1)} ms"
            results.append(
                f"{host}: {'✓ reachable' if reachable else '✗ unreachable'} (RTT: {rtt})"
            )
        except Exception as e:
            results.append(f"{host}: error — {e}")
    return f"Reachability {router_name}:\n" + "\n".join(results)


@tool
def check_ssh_access(router_name: str) -> str:
    """
    Diagnosa akses SSH ke router: ICMP ping + TCP port 22 + SSH banner check.
    Membedakan 4 skenario: routing failure, firewall DROP, firewall REJECT/SSH non-aktif,
    atau SSH ACL (source IP dibatasi di router).
    Gunakan tool ini saat get_system_info atau tool SSH lain gagal di router tertentu.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    hosts = list({e["host"] for e in get_router_entries(router_name)})
    results = []

    for host in hosts:
        lines = [f"Diagnosa SSH {router_name} ({host}):"]

        # 1. ICMP ping
        icmp_ok = False
        try:
            res = subprocess.run(
                ["ping", "-c", "2", "-W", "2", host],
                capture_output=True, text=True, timeout=8,
            )
            if res.returncode == 0:
                m = re.search(r"time=([\d.]+)", res.stdout)
                rtt = f"{m.group(1)} ms" if m else "?"
                lines.append(f"  ICMP ping   : ✓ reachable ({rtt})")
                icmp_ok = True
            else:
                lines.append("  ICMP ping   : ✗ unreachable")
        except Exception as e:
            lines.append(f"  ICMP ping   : error — {e}")

        # 2. TCP port 22
        tcp_status = "unknown"
        ssh_banner = None
        try:
            with socket.create_connection((host, 22), timeout=4) as sock:
                lines.append("  TCP port 22 : ✓ terbuka")
                tcp_status = "open"
                try:
                    sock.settimeout(3)
                    raw = sock.recv(64)
                    banner = raw.decode("ascii", errors="replace").strip()
                    if banner.startswith("SSH"):
                        lines.append(f"  SSH banner  : ✓ diterima ({banner[:48]})")
                        ssh_banner = "ok"
                    else:
                        lines.append(f"  SSH banner  : ✗ tidak valid (got: {repr(banner[:20])})")
                        ssh_banner = "invalid"
                except OSError:
                    lines.append("  SSH banner  : ✗ tidak diterima (koneksi diputus)")
                    ssh_banner = "dropped"
        except ConnectionRefusedError:
            lines.append("  TCP port 22 : ✗ Connection Refused")
            tcp_status = "refused"
        except socket.timeout:
            lines.append("  TCP port 22 : ✗ timeout (>4s)")
            tcp_status = "timeout"
        except OSError as e:
            lines.append(f"  TCP port 22 : ✗ {e}")
            tcp_status = "error"

        # 3. Diagnosis
        if not icmp_ok:
            dx = (
                "ROUTING FAILURE — Router tidak dapat dijangkau via ICMP. "
                "Cek apakah link/interface menuju router ini down."
            )
        elif tcp_status == "open" and ssh_banner == "ok":
            dx = "OK — SSH dapat diakses dari host ini. Error sebelumnya kemungkinan transien."
        elif tcp_status == "open" and ssh_banner in ("dropped", "invalid"):
            dx = (
                "SSH ACL — Port 22 terbuka (TCP 3-way handshake berhasil) tetapi "
                "SSH banner tidak dikirim router. Router kemungkinan membatasi SSH "
                "hanya dari network/IP tertentu via `/ip/ssh` allowed-addresses atau "
                "`/ip/firewall/filter`. "
                "Solusi: tambahkan IP sumber ini ke allowed-addresses di router tersebut, "
                "atau hubungi admin dari network yang diizinkan."
            )
        elif tcp_status == "refused":
            dx = (
                "SSH NONAKTIF atau REJECT — Port 22 aktif ditolak (RST). "
                "Kemungkinan SSH service dinonaktifkan atau firewall dengan action=reject."
            )
        elif tcp_status == "timeout":
            dx = (
                "FIREWALL DROP — Port 22 tidak merespons sama sekali. "
                "Firewall memblokir akses SSH dari sumber ini tanpa mengirim RST. "
                "Cek `/ip/firewall/filter/print` dari router yang bisa diakses."
            )
        else:
            dx = f"Tidak dapat ditentukan (ICMP={'ok' if icmp_ok else 'fail'}, TCP={tcp_status})."

        lines.append(f"  Diagnosis   : {dx}")
        results.append("\n".join(lines))

    return "\n\n".join(results)
