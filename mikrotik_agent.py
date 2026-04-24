#!/usr/bin/env python3
"""
MikroTik DHCP Lease Monitoring Agent
=====================================
Mengambil data DHCP lease dari beberapa router MikroTik via SSH secara paralel,
menghitung jumlah perangkat aktif, dan menyimpan hasilnya ke file lokal.

Penggunaan:
    python mikrotik_agent.py [--config config.yaml] [--dry-run FILE]

Contoh:
    python mikrotik_agent.py
    python mikrotik_agent.py --dry-run dhcp-lease-dti.txt
"""

import argparse
import getpass
import os
import re
import sys
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import paramiko
    from tabulate import tabulate
except ImportError:
    print("ERROR: Dependensi belum terinstall. Jalankan:")
    print("  pip install -r requirements.txt")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────

@dataclass
class LeaseEntry:
    """Representasi satu entri DHCP lease dari MikroTik."""
    index: str
    disabled: bool
    ip_address: str
    mac_address: str
    hostname: str
    server: str
    status: str           # "bound" atau "waiting"
    comment: str = ""     # dari baris ";;; ..."

    @property
    def is_active(self) -> bool:
        """Perangkat aktif = bound dan TIDAK disabled."""
        return self.status == "bound" and not self.disabled

    @property
    def is_inactive(self) -> bool:
        """Lease waiting dan tidak disabled."""
        return self.status == "waiting" and not self.disabled


@dataclass
class RouterResult:
    """Hasil query satu router."""
    name: str
    host: str
    dhcp_server: str
    success: bool
    leases: list[LeaseEntry] = field(default_factory=list)
    raw_output: str = ""
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total(self) -> int:
        return len(self.leases)

    @property
    def bound_count(self) -> int:
        return sum(1 for l in self.leases if l.is_active)

    @property
    def utbk_os_count(self) -> int:
        return sum(1 for l in self.leases if l.is_active and l.hostname == 'utbk-os')

    @property
    def other_count(self) -> int:
        return sum(1 for l in self.leases if l.is_active and l.hostname != 'utbk-os')

    @property
    def waiting_count(self) -> int:
        return sum(1 for l in self.leases if l.is_inactive)

    @property
    def disabled_count(self) -> int:
        return sum(1 for l in self.leases if l.disabled)


# ─────────────────────────────────────────────────────────────
# Parser Output MikroTik
# ─────────────────────────────────────────────────────────────

def parse_mikrotik_dhcp_output(raw_text: str) -> list[LeaseEntry]:
    leases = []
    lines = raw_text.splitlines()

    # Regex untuk tabular lama (fallback)
    inline_pattern = re.compile(
        r'^\s*(\d+)\s+'                       # group 1: index
        r'((?:[A-Z]\s+)*)'                    # group 2: flags (X, D, R, B …)
        r'((?:\d{1,3}\.){3}\d{1,3})'         # group 3: IP address
        r'\s+'
        r'([0-9A-Fa-f:]{17})'                # group 4: MAC address
        r'(?:\s+(.*))?$'                     # group 5: sisa string
    )
    data_pattern = re.compile(
        r'^\s+'                              # leading whitespace (indent)
        r'((?:\d{1,3}\.){3}\d{1,3})'        # group 1: IP address
        r'\s+'
        r'([0-9A-Fa-f:]{17})'               # group 2: MAC address
        r'(?:\s+(.*))?$'                     # group 3: sisa string
    )
    index_comment_pattern = re.compile(r'^\s*(\d+)\s+((?:[A-Z]\s+)*);;;\s*(.+)$')
    index_only_pattern = re.compile(r'^\s*(\d+)\s+((?:[A-Z]\s+)*)$')

    pending_entry = None

    for i, line in enumerate(lines):
        if not line.strip() or line.startswith('Flags:') or line.strip().startswith('#'):
            continue

        # Cek apakah baris menggunakan format TERSE (key=value)
        if 'mac-address=' in line and 'address=' in line:
            props = dict(re.findall(r'([a-zA-Z0-9\-]+)=(".*?"|\S+)', line))
            ip = props.get('address', '')
            mac = props.get('mac-address', '')
            server = props.get('server', '')
            status = props.get('status', 'unknown')
            hostname = props.get('host-name', '').strip('"')
            disabled_str = props.get('disabled', 'no')
            comment = props.get('comment', '').strip('"')
            
            idx_match = re.search(r'^\s*(\d+)', line)
            index = idx_match.group(1) if idx_match else '?'
            
            leases.append(LeaseEntry(
                index=index,
                disabled=(disabled_str == 'yes' or disabled_str == 'true' or 'X' in line.split('address=')[0]),
                ip_address=ip,
                mac_address=mac,
                hostname=hostname,
                server=server,
                status=status,
                comment=comment
            ))
            continue

        # Fallback parsing format tabular lama
        m_inline = inline_pattern.match(line)
        m_idx_comment = index_comment_pattern.match(line)
        m_idx_only = index_only_pattern.match(line)
        m_data = data_pattern.match(line)

        if m_inline:
            sisa = m_inline.group(5) or ''
            status = 'unknown'
            if 'bound' in sisa: status = 'bound'
            elif 'waiting' in sisa: status = 'waiting'
            
            leases.append(LeaseEntry(
                index=m_inline.group(1),
                disabled='X' in m_inline.group(2),
                ip_address=m_inline.group(3),
                mac_address=m_inline.group(4),
                hostname='', server='', status=status,
                comment=pending_entry['comment'] if pending_entry else ''
            ))
            pending_entry = None
            
        elif m_idx_comment:
            pending_entry = {'index': m_idx_comment.group(1), 'disabled': 'X' in m_idx_comment.group(2), 'comment': m_idx_comment.group(3).strip()}
        elif m_idx_only:
            pending_entry = {'index': m_idx_only.group(1), 'disabled': 'X' in m_idx_only.group(2), 'comment': ''}
        elif m_data:
            sisa = m_data.group(3) or ''
            status = 'unknown'
            if 'bound' in sisa: status = 'bound'
            elif 'waiting' in sisa: status = 'waiting'
            
            if pending_entry:
                leases.append(LeaseEntry(
                    index=pending_entry['index'], disabled=pending_entry['disabled'],
                    ip_address=m_data.group(1), mac_address=m_data.group(2),
                    hostname='', server='', status=status,
                    comment=pending_entry['comment']
                ))
                pending_entry = None

    return leases


# ─────────────────────────────────────────────────────────────
# SSH Client
# ─────────────────────────────────────────────────────────────

def ssh_run_command(
    host: str,
    username: str,
    password: str,
    command: str,
    port: int = 22,
    timeout: int = 15
) -> tuple[bool, str, str]:
    """
    Jalankan satu perintah di router via SSH.

    Returns:
        (success, output, error_message)
    """
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Trik untuk MikroTik: tambahkan +400w agar terminal sangat lebar (mencegah kolom terpotong)
        mt_username = username
        if "+" not in username:
            mt_username = f"{username}+400w"

        client.connect(
            hostname=host,
            port=port,
            username=mt_username,
            password=password,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')

        client.close()

        if error and not output:
            return False, '', f"Router error: {error.strip()}"

        return True, output, ''

    except paramiko.AuthenticationException:
        return False, '', "Autentikasi gagal — username/password salah"
    except paramiko.SSHException as e:
        return False, '', f"SSH error: {e}"
    except TimeoutError:
        return False, '', f"Timeout — tidak bisa terhubung ke {host}:{port}"
    except OSError as e:
        return False, '', f"Network error: {e}"
    finally:
        try:
            client.close()
        except Exception:
            pass


def ssh_get_dhcp_leases(
    host: str,
    username: str,
    password: str,
    dhcp_server: str,
    port: int = 22,
    timeout: int = 15,
    debug: bool = False,
    ros_version: int = 7
) -> tuple[bool, str, str]:
    """
    SSH ke router MikroTik dan ambil DHCP lease.
    Mendukung RouterOS v6 (space-path) dan v7 (slash-path).

    Returns:
        (success, output, error_message)
    """
    if ros_version == 6:
        # RouterOS v6: ip dhcp-server lease print without-paging where server=...
        command = f'ip dhcp-server lease print terse without-paging where server={dhcp_server}'
    else:
        # RouterOS v7: /ip/dhcp-server/lease/print without-paging where server=...
        command = f'/ip dhcp-server/lease/print terse without-paging where server={dhcp_server}'

    if debug:
        print(f"    [DEBUG] ROS v{ros_version} — Command: {command}")

    ok, output, error = ssh_run_command(host, username, password, command, port, timeout)

    if debug and ok:
        lines = output.splitlines()
        print(f"    [DEBUG] Raw output ({len(lines)} baris):")
        for line in lines[:20]:  # Tampilkan max 20 baris pertama
            print(f"    [DEBUG]   {repr(line)}")
        if len(lines) > 20:
            print(f"    [DEBUG]   ... ({len(lines)-20} baris lagi)")

    return ok, output, error


def list_dhcp_servers(
    host: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 15,
    ros_version: int = 7
) -> tuple[bool, list[str], str]:
    """
    Ambil daftar nama DHCP server yang ada di router.

    Returns:
        (success, [nama_server, ...], error_message)
    """
    if ros_version == 6:
        command = 'ip dhcp-server print without-paging'
    else:
        command = '/ip dhcp-server/print without-paging'

    ok, output, error = ssh_run_command(host, username, password, command, port, timeout)

    if not ok:
        return False, [], error

    # Parse nama dari kolom NAME di output
    # Format: "  0   nama-server   interface   ..."
    servers = []
    name_pattern = re.compile(r'^\s*\d+\s+(?:[A-Z]\s+)*(\S+)')
    for line in output.splitlines():
        if line.startswith('Flags:') or line.strip().startswith('#') or not line.strip():
            continue
        # Skip header
        if 'NAME' in line and 'INTERFACE' in line:
            continue
        m = name_pattern.match(line)
        if m:
            servers.append(m.group(1))

    return True, servers, ''


# ─────────────────────────────────────────────────────────────
# Worker — dijalankan paralel per router+server
# ─────────────────────────────────────────────────────────────

def query_router(
    router_name: str,
    host: str,
    dhcp_server: str,
    username: str,
    password: str,
    port: int,
    timeout: int,
    debug: bool = False,
    ros_version: int = 7
) -> RouterResult:
    """Query satu router untuk satu DHCP server."""
    print(f"  ⟳ Menghubungi {router_name} ({host}) — DHCP server: {dhcp_server} [ROS v{ros_version}] ...")

    success, raw_output, error = ssh_get_dhcp_leases(
        host=host,
        username=username,
        password=password,
        dhcp_server=dhcp_server,
        port=port,
        timeout=timeout,
        debug=debug,
        ros_version=ros_version
    )

    result = RouterResult(
        name=router_name,
        host=host,
        dhcp_server=dhcp_server,
        success=success,
        raw_output=raw_output,
        error=error
    )

    if success:
        result.leases = parse_mikrotik_dhcp_output(raw_output)
        if result.total == 0:
            # Koneksi berhasil tapi tidak ada lease — kemungkinan nama server salah
            print(f"  ⚠ {router_name}: 0 lease ditemukan untuk server='{dhcp_server}'")
            print(f"    → Cek nama DHCP server dengan: python mikrotik_agent.py --list-servers")
        else:
            print(f"  ✓ {router_name}: {result.bound_count} aktif (UTBK-OS: {result.utbk_os_count}, Other: {result.other_count}) / {result.total} total lease")
    else:
        print(f"  ✗ {router_name} ({host}): {error}")

    return result


# ─────────────────────────────────────────────────────────────
# Output & Reporting
# ─────────────────────────────────────────────────────────────

def save_raw_output(result: RouterResult, output_dir: Path):
    """Simpan raw output ke file teks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = result.timestamp.strftime('%Y%m%d_%H%M%S')
    safe_name = result.name.lower().replace(' ', '_').replace('/', '-')
    filename = output_dir / f"dhcp-lease-{safe_name}-{result.dhcp_server}-{timestamp_str}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Router  : {result.name} ({result.host})\n")
        f.write(f"# Server  : {result.dhcp_server}\n")
        f.write(f"# Diambil : {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total   : {result.total} | Bound: {result.bound_count} (UTBK-OS: {result.utbk_os_count}, Other: {result.other_count}) | Waiting: {result.waiting_count} | Disabled: {result.disabled_count}\n")
        f.write("─" * 70 + "\n")
        f.write(result.raw_output)

    return filename


def save_summary_report(results: list[RouterResult], output_dir: Path):
    """Simpan laporan ringkasan semua router ke file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = output_dir / f"summary-{timestamp_str}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(build_summary_text(results))

    return filename


def build_summary_text(results: list[RouterResult]) -> str:
    """Buat teks laporan ringkasan."""
    lines = []
    lines.append("=" * 65)
    lines.append("  LAPORAN DHCP LEASE — MONITORING PERANGKAT UTBK")
    lines.append(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 65)
    lines.append("")

    # Tabel per router
    table_rows = []
    total_bound = 0
    total_utbk_os = 0
    total_other = 0
    total_waiting = 0
    total_disabled = 0
    total_all = 0

    for r in results:
        if r.success:
            table_rows.append([
                r.name,
                r.host,
                r.dhcp_server,
                r.bound_count,
                r.utbk_os_count,
                r.other_count,
                r.waiting_count,
                r.disabled_count,
                r.total,
                "✓ OK"
            ])
            total_bound += r.bound_count
            total_utbk_os += r.utbk_os_count
            total_other += r.other_count
            total_waiting += r.waiting_count
            total_disabled += r.disabled_count
            total_all += r.total
        else:
            table_rows.append([
                r.name,
                r.host,
                r.dhcp_server,
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                f"✗ {r.error[:25]}..."
            ])

    headers = ["Router", "Host", "DHCP Server", "Bound", "UTBK-OS", "Other", "Waiting", "Disabled", "Total", "Status"]
    lines.append(tabulate(table_rows, headers=headers, tablefmt="rounded_outline"))
    lines.append("")

    # Total keseluruhan
    successful = [r for r in results if r.success]
    if successful:
        lines.append(f"  TOTAL PERANGKAT AKTIF (bound)   : {total_bound:>5}")
        lines.append(f"  - host-name=utbk-os             : {total_utbk_os:>5}")
        lines.append(f"  - host-name lain                : {total_other:>5}")
        lines.append(f"  Total lease waiting              : {total_waiting:>5}")
        lines.append(f"  Total disabled (tidak dihitung)  : {total_disabled:>5}")
        lines.append(f"  Total seluruh lease              : {total_all:>5}")
        lines.append(f"  Router berhasil diquery          : {len(successful)}/{len(results)}")

    # Error detail
    failed = [r for r in results if not r.success]
    if failed:
        lines.append("")
        lines.append("── Error Detail ──")
        for r in failed:
            lines.append(f"  ✗ {r.name} ({r.host}): {r.error}")

    lines.append("")
    lines.append("=" * 65)

    return "\n".join(lines)


def print_detail(results: list[RouterResult]):
    """Cetak detail lease untuk setiap router yang sukses."""
    for r in results:
        if not r.success:
            continue

        print(f"\n{'─'*65}")
        print(f"  Detail: {r.name} ({r.host}) — {r.dhcp_server}")
        print(f"{'─'*65}")

        rows = []
        for lease in r.leases:
            label = lease.comment if lease.comment else lease.hostname
            flag = "[X]" if lease.disabled else ""
            rows.append([
                lease.index,
                flag,
                lease.ip_address,
                lease.mac_address,
                label[:30],
                lease.status
            ])

        if rows:
            headers = ["#", "Flag", "IP Address", "MAC Address", "Label", "Status"]
            print(tabulate(rows, headers=headers, tablefmt="simple"))
        else:
            print("  (tidak ada lease ditemukan)")


# ─────────────────────────────────────────────────────────────
# Dry-run: parse file lokal tanpa SSH
# ─────────────────────────────────────────────────────────────

def dry_run(filepath: str) -> RouterResult:
    """Parse file DHCP lease lokal (untuk testing tanpa router)."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: File tidak ditemukan: {filepath}")
        sys.exit(1)

    raw = path.read_text(encoding='utf-8', errors='replace')
    leases = parse_mikrotik_dhcp_output(raw)

    result = RouterResult(
        name=f"[DRY-RUN] {path.stem}",
        host="localhost",
        dhcp_server="(dari file)",
        success=True,
        leases=leases,
        raw_output=raw
    )
    return result


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    """Load konfigurasi dari file YAML."""
    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: File konfigurasi tidak ditemukan: {config_path}")
        print("Buat file config.yaml terlebih dahulu (lihat contoh di README)")
        sys.exit(1)

    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description='MikroTik DHCP Lease Monitoring Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--config', default='config.yaml',
        help='Path ke file konfigurasi YAML (default: config.yaml)'
    )
    parser.add_argument(
        '--dry-run', metavar='FILE',
        help='Parse file DHCP lease lokal tanpa SSH (untuk testing)'
    )
    parser.add_argument(
        '--detail', action='store_true',
        help='Tampilkan daftar lengkap semua lease (verbose)'
    )
    parser.add_argument(
        '--no-save', action='store_true',
        help='Jangan simpan output ke file'
    )
    parser.add_argument(
        '--list-servers', action='store_true',
        help='Tampilkan daftar DHCP server yang tersedia di setiap router'
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Tampilkan raw SSH output untuk troubleshooting'
    )
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║      MikroTik DHCP Lease Monitoring Agent                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # ── Mode dry-run ──────────────────────────────────────────
    if args.dry_run:
        print(f"[DRY-RUN] Parsing file: {args.dry_run}")
        result = dry_run(args.dry_run)
        results = [result]

        print(f"\nHasil:")
        print(f"  Total lease  : {result.total}")
        print(f"  Bound (aktif): {result.bound_count}")
        print(f"    - UTBK-OS  : {result.utbk_os_count}")
        print(f"    - Other    : {result.other_count}")
        print(f"  Waiting      : {result.waiting_count}")
        print(f"  Disabled     : {result.disabled_count}")

        if args.detail:
            print_detail(results)
        print()
        print(build_summary_text(results))
        return

    # ── Mode normal — SSH ke router ───────────────────────────
    config = load_config(args.config)
    ssh_cfg = config.get('ssh', {})
    output_dir = Path(config.get('output_dir', 'output'))

    username = ssh_cfg.get('username', 'admin')
    password = ssh_cfg.get('password', '')
    port = int(ssh_cfg.get('port', 22))
    timeout = int(ssh_cfg.get('timeout', 15))

    # Minta password jika belum ada di config
    if not password:
        print(f"Masukkan password SSH untuk user '{username}':")
        password = getpass.getpass("Password: ")
        print()

    routers = config.get('routers', [])
    if not routers:
        print("ERROR: Tidak ada router yang dikonfigurasi di config.yaml")
        sys.exit(1)

    # ── Mode list-servers: tampilkan DHCP server yang tersedia ─
    if args.list_servers:
        print("Mendapatkan daftar DHCP server dari setiap router...\n")
        for router in routers:
            host = router['host']
            name = router['name']
            ros_version = int(router.get('ros_version', 7))
            print(f"  Router: {name} ({host}) [ROS v{ros_version}]")
            ok, servers, err = list_dhcp_servers(host, username, password, port, timeout, ros_version)
            if ok:
                if servers:
                    for s in servers:
                        configured = router.get('dhcp_servers', [])
                        marker = " ← (dikonfigurasi)" if s in configured else ""
                        print(f"    • {s}{marker}")
                else:
                    print("    (tidak ada DHCP server ditemukan)")
            else:
                print(f"    ✗ Gagal: {err}")
            print()
        return

    # Buat task list (router × dhcp_servers)
    tasks = []
    for router in routers:
        for dhcp_server in router.get('dhcp_servers', []):
            tasks.append({
                'name': router['name'],
                'host': router['host'],
                'dhcp_server': dhcp_server,
                'ros_version': int(router.get('ros_version', 7))
            })

    print(f"Akan query {len(tasks)} task dari {len(routers)} router...\n")

    # ── Jalankan paralel ──────────────────────────────────────
    results: list[RouterResult] = []
    max_workers = min(len(tasks), 10)  # Maksimal 10 koneksi paralel

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                query_router,
                t['name'], t['host'], t['dhcp_server'],
                username, password, port, timeout,
                args.debug, t['ros_version']
            ): t
            for t in tasks
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                task = futures[future]
                print(f"  ✗ {task['name']} ({task['host']}): Unexpected error: {e}")
                results.append(RouterResult(
                    name=task['name'],
                    host=task['host'],
                    dhcp_server=task['dhcp_server'],
                    success=False,
                    error=str(e)
                ))

    # Urutkan sesuai urutan config
    name_order = {t['name'] + t['dhcp_server']: i for i, t in enumerate(tasks)}
    results.sort(key=lambda r: name_order.get(r.name + r.dhcp_server, 999))

    # ── Tampilkan hasil ───────────────────────────────────────
    print()
    if args.detail:
        print_detail(results)
        print()

    print(build_summary_text(results))

    # ── Simpan ke file ────────────────────────────────────────
    if not args.no_save:
        print("\nMenyimpan output ke file...")
        for r in results:
            if r.success and r.raw_output:
                saved = save_raw_output(r, output_dir)
                print(f"  → {saved}")

        summary_file = save_summary_report(results, output_dir)
        print(f"  → {summary_file} (ringkasan)")
        print()


if __name__ == '__main__':
    main()
