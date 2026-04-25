#!/usr/bin/env python3
"""
Generate daily DHCP lease reports in Markdown format.
Reads all dhcp-lease-*.txt files from output/ directory and creates
one report per day in laporan/ directory.
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


def _load_dotenv() -> None:
    """Load .env file into os.environ if present."""
    env_file = Path(__file__).parent / ".env"
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
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "output"
LAPORAN_DIR = Path(__file__).parent / "laporan"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6:35b-a3b-q8_0")
OLLAMA_TIMEOUT = 300  # seconds per request


def call_ollama(prompt: str) -> str:
    """Call Ollama API and return generated text. Returns empty string on failure."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 1024, "temperature": 0.3},
                "think": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"  [AI] Warning: Ollama tidak tersedia: {e}")
        return ""


def parse_header(line):
    """Parse the header line: # Total : 273 | Bound: 199 (UTBK-OS: 196, Other: 3) | Waiting: 63 | Disabled: 11"""
    m = re.match(
        r"#\s*Total\s*:\s*(\d+)\s*\|\s*Bound:\s*(\d+)\s*\((?:UTBK-OS:\s*(\d+),\s*Other:\s*(\d+)\)|Other:\s*(\d+))\s*\)\s*\|\s*Waiting:\s*(\d+)\s*\|\s*Disabled:\s*(\d+)",
        line,
    )
    if m:
        return {
            "total": int(m.group(1)),
            "bound": int(m.group(2)),
            "utbk_os": int(m.group(3)) if m.group(3) else 0,
            "other": int(m.group(4)) if m.group(4) else int(m.group(5) or 0),
            "waiting": int(m.group(6)),
            "disabled": int(m.group(7)),
        }
    return None


def extract_mac(entry_line):
    """Extract MAC address from an entry line."""
    m = re.search(r"mac-address=(\S+)", entry_line)
    return m.group(1).upper() if m else None


def extract_entry_info(entry_line):
    """Extract key info from an entry line."""
    ip = re.search(r"address=(\S+)", entry_line)
    mac = re.search(r"mac-address=(\S+)", entry_line)
    comment = re.search(r"comment=(\S+)", entry_line)
    hostname = re.search(r"host-name=(\S+)", entry_line)
    client_id = re.search(r"client-id=(\S+)", entry_line)
    status = re.search(r"status=(\S+)", entry_line)
    last_seen = re.search(r"last-seen=(\S+)", entry_line)
    age = re.search(r"age=(\S+)", entry_line)
    expires = re.search(r"expires-after=(\S+)", entry_line)
    return {
        "ip": ip.group(1) if ip else "-",
        "mac": mac.group(1).upper() if mac else "-",
        "comment": comment.group(1) if comment else "-",
        "hostname": hostname.group(1) if hostname else "-",
        "client_id": client_id.group(1) if client_id else "-",
        "status": status.group(1) if status else "-",
        "last_seen": last_seen.group(1) if last_seen else "-",
        "age": age.group(1) if age else "-",
        "expires": expires.group(1) if expires else "-",
    }


def parse_file(filepath):
    """Parse a single dhcp-lease file and return header info + entry counts."""
    header = None
    bound_count = 0
    waiting_count = 0
    disabled_count = 0
    utbk_os_count = 0
    other_count = 0
    entries = []
    mac_set = set()

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                h = parse_header(line)
                if h:
                    header = h
                continue
            if not line or line.startswith("─"):
                continue

            is_disabled = line.startswith("X ")

            if "status=bound" in line:
                bound_count += 1
                if "host-name=utbk-os" in line:
                    utbk_os_count += 1
                else:
                    other_count += 1
            elif "status=waiting" in line:
                waiting_count += 1
            elif "status=disabled" in line:
                disabled_count += 1

            if not is_disabled:
                entries.append(line)
                mac = extract_mac(line)
                if mac:
                    mac_set.add(mac)

    return {
        "header": header,
        "bound": bound_count,
        "waiting": waiting_count,
        "disabled": disabled_count,
        "utbk_os": utbk_os_count,
        "other": other_count,
        "total": bound_count + waiting_count + disabled_count,
        "entries": entries,
        "mac_set": mac_set,
    }


def extract_server_name(filename):
    """Extract server name from filename like dhcp-lease-dti-dhcp-lab-tik-20260424_131041.txt"""
    m = re.match(r"dhcp-lease-(.+?)-(\d{8}_\d{6})\.txt", filename)
    if m:
        return m.group(1), m.group(2)
    return filename, ""


def extract_date(filename):
    """Extract date from filename."""
    m = re.match(r".+(\d{8})_\d{6}\.txt", filename)
    if m:
        return m.group(1)
    return ""


def format_date(date_str):
    """Convert 20260424 to 24 April 2026."""
    months = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    y = int(date_str[:4])
    m = int(date_str[4:6])
    d = int(date_str[6:8])
    return f"{d:02d} {months[m-1]} {y}"


def find_anomalies(server_data):
    """Find anomalies in DHCP lease entries, tracking per server."""
    anomalies = []

    waiting_entries = []  # list of (server, entry)
    bound_entries = []    # list of (server, entry)
    disabled_entries = [] # list of (server, entry)

    for server, data in server_data.items():
        for entry in data["entries"]:
            if "status=waiting" in entry:
                waiting_entries.append((server, entry))
            elif "status=bound" in entry:
                bound_entries.append((server, entry))
            elif "status=disabled" in entry or entry.startswith("X "):
                disabled_entries.append((server, entry))

    # Anomaly 1: Waiting > 1 day
    long_waiting = []
    for server, e in waiting_entries:
        m_last = re.search(r"last-seen=(\d+w\d+d\d+h\d+m\d+s)", e)
        m_age = re.search(r"age=(\d+w\d+d\d+h\d+m\d+s)", e)
        if m_last or m_age:
            time_str = m_age.group(1) if m_age else m_last.group(1)
            total_seconds = parse_duration(time_str)
            if total_seconds > 86400:  # > 1 day
                ip = re.search(r"address=(\S+)", e)
                comment = re.search(r"comment=(\S+)", e)
                hostname = re.search(r"host-name=(\S+)", e)
                mac = re.search(r"mac-address=(\S+)", e)
                long_waiting.append({
                    "server": server,
                    "ip": ip.group(1) if ip else "?",
                    "comment": comment.group(1) if comment else "-",
                    "hostname": hostname.group(1) if hostname else "-",
                    "mac": mac.group(1) if mac else "-",
                    "time": time_str,
                    "seconds": total_seconds,
                })

    if long_waiting:
        long_waiting.sort(key=lambda x: x["seconds"], reverse=True)
        anomalies.append({
            "title": "Perangkat Waiting Sudah Berhari-hari",
            "severity": "CRITICAL",
            "emoji": "🔴",
            "description": f"Terdapat **{len(long_waiting)} perangkat waiting** yang sudah mencoba mendapatkan IP selama lebih dari 1 hari.",
            "data": long_waiting,
            "columns": ["IP", "Comment", "Hostname", "MAC", "Durasi"],
            "keys": ["ip", "comment", "hostname", "mac", "time"],
            "recommendation": "Cek koneksi fisik dan konfigurasi DHCP client. Jika tidak digunakan, disable entri.",
        })

    # Anomaly 2: Waiting > 2 weeks
    very_long_waiting = []
    for server, e in waiting_entries:
        m_last = re.search(r"last-seen=(\d+w\d+d\d+h\d+m\d+s)", e)
        if m_last:
            time_str = m_last.group(1)
            total_seconds = parse_duration(time_str)
            if total_seconds > 1209600:  # > 2 weeks
                ip = re.search(r"address=(\S+)", e)
                comment = re.search(r"comment=(\S+)", e)
                hostname = re.search(r"host-name=(\S+)", e)
                very_long_waiting.append({
                    "server": server,
                    "ip": ip.group(1) if ip else "?",
                    "comment": comment.group(1) if comment else "-",
                    "hostname": hostname.group(1) if hostname else "-",
                    "time": time_str,
                    "seconds": total_seconds,
                })

    if very_long_waiting:
        very_long_waiting.sort(key=lambda x: x["seconds"], reverse=True)
        anomalies.append({
            "title": "Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu",
            "severity": "HIGH",
            "emoji": "🔴",
            "description": f"Terdapat **{len(very_long_waiting)} perangkat waiting** yang `last-seen` sudah lebih dari 2 minggu.",
            "data": very_long_waiting,
            "columns": ["IP", "Comment", "Hostname", "Last Seen"],
            "keys": ["ip", "comment", "hostname", "time"],
            "recommendation": "Disable/hapus entri ini untuk bebaskan IP pool.",
        })

    # Anomaly 3: Bound > 3 days
    old_bound = []
    for server, e in bound_entries:
        m_age = re.search(r"age=(\d+w\d+d\d+h\d+m\d+s)", e)
        if m_age:
            time_str = m_age.group(1)
            total_seconds = parse_duration(time_str)
            if total_seconds > 259200:  # > 3 days
                ip = re.search(r"address=(\S+)", e)
                comment = re.search(r"comment=(\S+)", e)
                hostname = re.search(r"host-name=(\S+)", e)
                expires = re.search(r"expires-after=(\S+)", e)
                old_bound.append({
                    "server": server,
                    "ip": ip.group(1) if ip else "?",
                    "comment": comment.group(1) if comment else "-",
                    "hostname": hostname.group(1) if hostname else "-",
                    "age": time_str,
                    "expires": expires.group(1) if expires else "-",
                    "seconds": total_seconds,
                })

    if old_bound:
        old_bound.sort(key=lambda x: x["seconds"], reverse=True)
        anomalies.append({
            "title": "Perangkat Bound Terlalu Lama (> 3 Hari)",
            "severity": "MEDIUM",
            "emoji": "🟡",
            "description": f"Terdapat **{len(old_bound)} perangkat bound** yang sudah lebih dari 3 hari.",
            "data": old_bound,
            "columns": ["IP", "Comment", "Hostname", "Age", "Expires After"],
            "keys": ["ip", "comment", "hostname", "age", "expires"],
            "recommendation": "Verifikasi apakah perangkat masih digunakan.",
        })

    # Anomaly 4: Disabled entries
    if disabled_entries:
        disabled_info = []
        for server, e in disabled_entries:
            ip = re.search(r"address=(\S+)", e)
            mac = re.search(r"mac-address=(\S+)", e)
            comment = re.search(r"comment=(\S+)", e)
            disabled_info.append({
                "server": server,
                "ip": ip.group(1) if ip else "?",
                "mac": mac.group(1) if mac else "-",
                "comment": comment.group(1) if comment else "-",
            })
        anomalies.append({
            "title": "Entri Disabled IP-nya Masih Tersisa di Pool",
            "severity": "MEDIUM",
            "emoji": "🟡",
            "description": f"**{len(disabled_entries)} entri disabled** masih memakan slot IP di pool DHCP.",
            "data": disabled_info,
            "columns": ["IP", "MAC Address", "Comment"],
            "keys": ["ip", "mac", "comment"],
            "recommendation": "Gunakan `remove` (bukan hanya disable) untuk entri yang sudah tidak diperlukan.",
        })

    return anomalies


def parse_duration(duration_str):
    """Parse duration string like 2w3d4h5m6s to total seconds."""
    total = 0
    patterns = [
        (r"(\d+)w", 604800),
        (r"(\d+)d", 86400),
        (r"(\d+)h", 3600),
        (r"(\d+)m", 60),
        (r"(\d+)s", 1),
    ]
    for pattern, multiplier in patterns:
        m = re.search(pattern, duration_str)
        if m:
            total += int(m.group(1)) * multiplier
    return total


def detect_new_devices(current_date, current_data, all_previous_data):
    """Detect new devices (by MAC) that appeared on this date but not in previous dates."""
    new_devices = []
    disconnected_devices = []

    # Collect all MACs from previous days
    previous_macs = set()
    previous_info = {}
    for prev_date, prev_servers in all_previous_data.items():
        for server, data in prev_servers.items():
            for mac in data.get("mac_set", set()):
                previous_macs.add(mac)
                if mac not in previous_info:
                    previous_info[mac] = {"first_seen": prev_date, "server": server}

    # Check current devices
    current_macs = set()
    current_info = {}
    for server, data in current_data.items():
        for entry in data.get("entries", []):
            mac = extract_mac(entry)
            if mac:
                current_macs.add(mac)
                if mac not in current_info:
                    current_info[mac] = extract_entry_info(entry)
                    current_info[mac]["server"] = server

    # Find new devices (in current but not in previous)
    new_macs = current_macs - previous_macs
    for mac in sorted(new_macs):
        info = current_info.get(mac, {})
        new_devices.append({
            "mac": mac,
            "ip": info.get("ip", "-"),
            "comment": info.get("comment", "-"),
            "hostname": info.get("hostname", "-"),
            "client_id": info.get("client_id", "-"),
            "status": info.get("status", "-"),
            "server": info.get("server", "-"),
        })

    # Find disconnected devices (in previous but not in current)
    # Only consider devices that were bound or waiting (not disabled)
    disconnected_macs = previous_macs - current_macs
    for mac in sorted(disconnected_macs):
        prev_info = previous_info.get(mac, {})
        # Skip if this was a disabled device
        if mac in previous_info:
            # Check if it was previously bound/waiting
            pass
        disconnected_devices.append({
            "mac": mac,
            "first_seen": prev_info.get("first_seen", "-"),
            "server": prev_info.get("server", "-"),
        })

    return new_devices, disconnected_devices


def get_subnet(ip):
    """Extract /24 subnet from IP."""
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return ip

def get_location(comment):
    """Extract lab number from comment."""
    # Try multiple patterns for lab identification
    patterns = [
        r'(Lab\d+)',           # Lab1, Lab2, etc.
        r'(LAB-\w+-\d+)',      # LAB-UTBK-26, LAB-SIM-01, etc.
        r'(Lab[A-Z]\d+)',      # LabA, LabB, etc.
        r'(Lab[A-Z]\.\d+)',    # Lab A.1, etc.
    ]
    for pattern in patterns:
        m = re.search(pattern, comment, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return "Other"


# Terms that indicate the model translated technical terms (should not appear)
_TRANSLATED_TERMS = {
    "terikat": "`bound`",
    "menunggu": "`waiting`",
    "dinonaktifkan": "`disabled`",
    "sewa jaringan": "`lease`",
    "kumpulan ip": "`IP pool`",
    "kolam ip": "`IP pool`",
    "kolam alamat": "`IP pool`",
    "jaringan lokal": "`subnet`",
    "alamat mac": "`MAC address`",
    "alamat ip": "`IP address`",
}


def validate_narrative(text: str) -> str:
    """Replace translated technical terms with correct English terms."""
    if not text:
        return text
    result = text
    for wrong, correct in _TRANSLATED_TERMS.items():
        # Case-insensitive replacement
        import re as _re
        result = _re.sub(wrong, correct, result, flags=_re.IGNORECASE)
    return result


def build_ai_narratives(
    date_display,
    total_all, total_bound, total_waiting, total_disabled,
    total_utbk, total_other,
    server_data,
    anomalies,
    trend_data,
    new_devices, disconnected_devices,
    sorted_subnets,
):
    """Generate AI narratives for each report section using Ollama in parallel."""

    waiting_pct = (total_waiting / total_all * 100) if total_all else 0
    bound_pct = (total_bound / total_all * 100) if total_all else 0
    utbk_pct = (total_utbk / total_bound * 100) if total_bound else 0
    critical_count = sum(1 for a in anomalies if a["severity"] == "CRITICAL")
    high_count = sum(1 for a in anomalies if a["severity"] == "HIGH")
    medium_count = sum(1 for a in anomalies if a["severity"] == "MEDIUM")
    total_anomaly_devices = sum(len(a["data"]) for a in anomalies)

    critical_subnets = [s for s, c in sorted_subnets if (c / 254 * 100) > 90]
    warning_subnets = [s for s, c in sorted_subnets if 70 < (c / 254 * 100) <= 90]

    trend_summary = ""
    if trend_data and len(trend_data) >= 2:
        prev = trend_data[-2]
        curr = trend_data[-1]
        delta_bound = curr["bound"] - prev["bound"]
        delta_waiting = curr["waiting"] - prev["waiting"]
        trend_summary = f"Dibanding hari sebelumnya: bound berubah {delta_bound:+d}, waiting berubah {delta_waiting:+d}."

    STYLE = (
        "Gunakan bahasa Indonesia yang ringkas dan langsung. "
        "Istilah teknis jaringan JANGAN diterjemahkan — tulis apa adanya: "
        "`bound`, `waiting`, `lease`, `subnet`, `pool`, `DHCP server`, `router`, `MAC address`, `IP address`, `disabled`. "
        "Gunakan backtick untuk setiap kata teknis. "
        "Jangan gunakan bullet points. Jangan ulangi angka mentah, berikan interpretasi. "
        "Tulis seolah-olah kamu adalah network engineer yang menulis laporan harian untuk manager."
    )

    EXAMPLE_STYLE = (
        "\n\nContoh output yang benar:\n"
        "\"Kondisi `lease` secara keseluruhan stabil dengan mayoritas perangkat dalam status `bound`. "
        "Rasio `waiting` masih di bawah threshold normal sehingga tidak memerlukan tindakan segera. "
        "Subnet `10.39.0.0/24` perlu dipantau karena utilisasinya mendekati batas waspada.\"\n\n"
        "Sekarang tulis untuk data berikut:"
    )

    prompts = {
        "executive": (
            f"Kamu adalah network engineer kampus. {STYLE}{EXAMPLE_STYLE}\n"
            f"Tulis ringkasan eksekutif (3-4 kalimat) kondisi DHCP `lease` berikut:\n"
            f"Tanggal: {date_display}\n"
            f"Total perangkat: {total_all} (`bound`: {total_bound} ({bound_pct:.1f}%), `waiting`: {total_waiting} ({waiting_pct:.1f}%), `disabled`: {total_disabled})\n"
            f"UTBK-OS: {total_utbk} dari {total_bound} `bound` ({utbk_pct:.1f}%)\n"
            f"Anomali: {len(anomalies)} jenis, {total_anomaly_devices} perangkat terdampak ({critical_count} CRITICAL, {high_count} HIGH, {medium_count} MEDIUM)\n"
            f"`Subnet` kritis (>90%): {', '.join(critical_subnets) if critical_subnets else 'tidak ada'}\n"
            f"{trend_summary}\n"
            f"Fokus pada kondisi yang perlu perhatian segera dan rekomendasi utama."
        ),
        "section1": (
            f"{STYLE}\n"
            f"Contoh output: \"Mayoritas perangkat berhasil mendapatkan `lease` dengan status `bound`. "
            f"Namun rasio `waiting` yang tinggi mengindikasikan ada perangkat yang gagal mendapatkan `IP address` — perlu investigasi segera.\"\n\n"
            f"Sekarang analisis kondisi `lease` DHCP berikut dalam 2-3 kalimat:\n"
            f"`bound`: {total_bound} ({bound_pct:.1f}%), `waiting`: {total_waiting} ({waiting_pct:.1f}%), `disabled`: {total_disabled}\n"
            f"Threshold normal: `waiting` < 10% dari total. Apakah kondisi saat ini normal atau perlu perhatian?"
        ),
        "section2": (
            f"{STYLE}\n"
            f"Contoh output: \"Tren `bound` selama 3 hari terakhir menunjukkan penurunan bertahap yang perlu diwaspadai. "
            f"Lonjakan `waiting` pada 22 April mengindikasikan adanya gangguan sementara pada `DHCP server`.\"\n\n"
            f"Sekarang analisis tren historis `bound` dan `waiting` dalam 2-3 kalimat:\n"
            f"Data historis (terbaru terakhir): {[(t['date'], t['bound'], t['waiting']) for t in trend_data[-5:]]}\n"
            f"{trend_summary}"
        ) if trend_data else "",
        "section3": (
            f"{STYLE}\n"
            f"Contoh output: \"`IP pool` secara keseluruhan masih aman, namun `subnet` `10.39.0.0/24` sudah masuk kategori waspada dengan utilisasi mendekati 80%. "
            f"Jika pertumbuhan perangkat berlanjut, ekspansi `pool` perlu dipertimbangkan dalam waktu dekat.\"\n\n"
            f"Sekarang analisis utilisasi `IP pool` dalam 2-3 kalimat:\n"
            f"`subnet` kritis (>90%): {critical_subnets if critical_subnets else 'tidak ada'}\n"
            f"`subnet` waspada (70-90%): {warning_subnets if warning_subnets else 'tidak ada'}\n"
            f"Total `subnet`: {len(sorted_subnets)}\n"
            f"Apakah ada risiko kekurangan IP? Apa yang perlu dilakukan?"
        ),
        "section5": (
            f"{STYLE}\n"
            f"Contoh output: \"Distribusi beban antar `DHCP server` tidak merata — beberapa server menangani ratusan `lease` sementara yang lain hampir kosong. "
            f"`DHCP server` `dti-dhcp-lab-tik` mencatat konsentrasi `waiting` tertinggi dan perlu diperiksa konfigurasinya.\"\n\n"
            f"Sekarang analisis distribusi beban antar `DHCP server` dalam 2-3 kalimat:\n"
            f"Server dan jumlah perangkat (`bound`, `waiting`): { {s: (d['bound'], d['waiting']) for s, d in server_data.items()} }\n"
            f"Apakah beban merata? `DHCP server` mana yang paling banyak menangani perangkat `waiting`?"
        ),
        "section7": (
            f"{STYLE}\n"
            f"Contoh output: \"Terdapat sejumlah perangkat baru yang terdeteksi hari ini berdasarkan `MAC address` yang belum pernah muncul sebelumnya. "
            f"Perangkat yang disconnect perlu diverifikasi apakah memang sudah tidak digunakan atau ada masalah konektivitas.\"\n\n"
            f"Sekarang analisis perangkat baru dan disconnect dalam 2-3 kalimat:\n"
            f"Perangkat baru: {len(new_devices)}, perangkat disconnect: {len(disconnected_devices)}\n"
            f"Apakah ada indikasi pergerakan perangkat yang tidak wajar atau perlu investigasi?"
        ) if (new_devices or disconnected_devices) else "",
        "section8": (
            f"{STYLE}\n"
            f"Contoh output: \"Anomali terkonsentrasi pada dua `router` utama yang menangani sebagian besar `lease` kampus. "
            f"`Router` `fia-dhcp-2380-lab` memiliki jumlah anomali CRITICAL tertinggi dan harus menjadi prioritas penanganan pertama.\"\n\n"
            f"Sekarang analisis distribusi anomali per `router` dalam 2-3 kalimat:\n"
            f"Total anomali: {total_anomaly_devices} perangkat, {len(anomalies)} jenis "
            f"(CRITICAL: {critical_count}, HIGH: {high_count}, MEDIUM: {medium_count}).\n"
            f"`Router` dengan anomali: { list(set(item.get('server', '-') for a in anomalies for item in a['data'])) }\n"
            f"`Router` mana yang paling membutuhkan perhatian?"
        ),
        "section9": (
            f"{STYLE}\n"
            f"Contoh output: \"Anomali `waiting` yang sudah berlangsung berminggu-minggu menunjukkan perangkat yang tidak pernah berhasil mendapatkan `lease` dan kemungkinan sudah tidak aktif. "
            f"Entri ini sebaiknya segera di-`disabled` atau dihapus untuk membebaskan slot di `IP pool`.\"\n\n"
            f"Sekarang jelaskan implikasi dan urgensi anomali berikut dalam 2-3 kalimat:\n"
            f"Anomali: { [(a['title'], a['severity'], len(a['data'])) for a in anomalies] }\n"
            f"`waiting` terlama: { max((item.get('time', '0s') for a in anomalies for item in a['data'] if 'Waiting' in a['title']), default='N/A') }"
        ) if anomalies else "",
    }

    print("  [AI] Generating AI narratives in parallel...")

    narratives = {key: "" for key in prompts}
    non_empty = {k: v for k, v in prompts.items() if v}

    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(call_ollama, prompt): key for key, prompt in non_empty.items()}
        for future in as_completed(futures):
            key = futures[future]
            raw = future.result()
            narratives[key] = validate_narrative(raw)
            print(f"  [AI] ✓ Narrative ready: {key}")

    return narratives

def generate_report(date_str, server_data, all_previous_data=None):
    """Generate a markdown report for a given date."""
    date_display = format_date(date_str)

    # Aggregate totals
    total_bound = sum(d["bound"] for d in server_data.values())
    total_waiting = sum(d["waiting"] for d in server_data.values())
    total_disabled = sum(d["disabled"] for d in server_data.values())
    total_utbk = sum(d["utbk_os"] for d in server_data.values())
    total_other = sum(d["other"] for d in server_data.values())
    total_all = total_bound + total_waiting + total_disabled

    # Collect all entries for anomaly detection (still needed for IP Pool Health)
    all_entries = []
    for d in server_data.values():
        all_entries.extend(d["entries"])

    # Find anomalies
    anomalies = find_anomalies(server_data)

    # Detect new and disconnected devices
    new_devices = []
    disconnected_devices = []
    if all_previous_data:
        new_devices, disconnected_devices = detect_new_devices(
            date_str, server_data, all_previous_data
        )

    # Historical Trend (7 days)
    trend_data = []
    if all_previous_data:
        sorted_dates = sorted(all_previous_data.keys())
        all_dates = sorted_dates + [date_str]
        
        for d in all_dates:
            if d == date_str:
                servers = server_data
            else:
                servers = all_previous_data.get(d, {})
            
            total_b = sum(s["bound"] for s in servers.values())
            total_w = sum(s["waiting"] for s in servers.values())
            total_all = sum(s["total"] for s in servers.values())
            trend_data.append({
                "date": format_date(d),
                "bound": total_b,
                "waiting": total_w,
                "total": total_all
            })

    # IP Pool Health
    subnet_usage = defaultdict(int)
    for entry in all_entries:
        ip_m = re.search(r"address=(\S+)", entry)
        if ip_m:
            subnet = get_subnet(ip_m.group(1))
            subnet_usage[subnet] += 1
    
    sorted_subnets = sorted(subnet_usage.items(), key=lambda x: x[1], reverse=True)

    # Generate AI narratives in parallel
    print(f"  [AI] Generating narratives for {date_display}...")
    narratives = build_ai_narratives(
        date_display=date_display,
        total_all=total_all,
        total_bound=total_bound,
        total_waiting=total_waiting,
        total_disabled=total_disabled,
        total_utbk=total_utbk,
        total_other=total_other,
        server_data=server_data,
        anomalies=anomalies,
        trend_data=trend_data,
        new_devices=new_devices,
        disconnected_devices=disconnected_devices,
        sorted_subnets=sorted_subnets,
    )

    # Build report
    lines = []
    lines.append(f"# 📊 Laporan DHCP Lease — {date_display}")
    lines.append("")
    lines.append(f"**Tanggal:** {date_display}")
    lines.append(f"**Total Server:** {len(server_data)}")
    lines.append(f"**File Sumber:** {len(server_data)} file di direktori `output/`")
    if all_previous_data:
        prev_total = sum(
            sum(d["total"] for d in servers.values())
            for servers in all_previous_data.values()
        )
        lines.append(f"**Perbandingan:** {total_all} perangkat hari ini vs {prev_total} perangkat hari sebelumnya")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    if narratives.get("executive"):
        lines.append("## 🗒️ Ringkasan Eksekutif")
        lines.append("")
        lines.append(narratives["executive"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # Section 1: Summary
    lines.append("## 1. Ringkasan Status")
    lines.append("")
    if narratives.get("section1"):
        lines.append(narratives["section1"])
        lines.append("")
    lines.append("| Status | Jumlah | Persentase |")
    lines.append("|---|---|---|")
    lines.append(f"| **Bound** | {total_bound} | {total_bound/total_all*100:.1f}% |")
    lines.append(f"| **Waiting** | {total_waiting} | {total_waiting/total_all*100:.1f}% |")
    lines.append(f"| **Disabled (X)** | {total_disabled} | {total_disabled/total_all*100:.1f}% |")
    lines.append(f"| **Total** | **{total_all}** | 100% |")
    lines.append("")

    # Section 2: Historical Trend
    if trend_data:
        lines.append("## 2. 📈 Tren Historis (7 Hari Terakhir)")
        lines.append("")
        if narratives.get("section2"):
            lines.append(narratives["section2"])
            lines.append("")
        lines.append("| Tanggal | Bound | Waiting | Total |")
        lines.append("|---|---|---|---|")
        for t in trend_data:
            lines.append(f"| {t['date']} | {t['bound']} | {t['waiting']} | {t['total']} |")
        lines.append("")

    # Section 3: IP Pool Health
    lines.append("## 3. 📊 Utilisasi IP Pool")
    lines.append("")
    if narratives.get("section3"):
        lines.append(narratives["section3"])
        lines.append("")
    lines.append("| Subnet | Used | Total (/24) | Usage % | Status |")
    lines.append("|---|---|---|---|---|")
    for subnet, count in sorted_subnets:
        total_ips = 254
        usage_pct = (count / total_ips) * 100
        if usage_pct > 90:
            status = "🔴 Kritis"
        elif usage_pct > 70:
            status = "🟡 Waspada"
        else:
            status = "🟢 Normal"
        lines.append(f"| {subnet} | {count} | {total_ips} | {usage_pct:.1f}% | {status} |")
    lines.append("")

    # Section 4: UTBK-OS
    lines.append("## 4. Distribusi Perangkat UTBK-OS")
    lines.append("")
    lines.append("| Kategori | Jumlah |")
    lines.append("|---|---|")
    lines.append(f"| Bound + UTBK-OS | {total_utbk} |")
    lines.append(f"| Bound + Other (non-UTBK) | {total_other} |")
    utbk_waiting = total_waiting  # approximate
    lines.append(f"| **Total UTBK-OS** | **{total_utbk}** |")
    lines.append("")
    if total_bound > 0:
        lines.append(f"> **Rasio UTBK-OS terhadap Bound:** {total_utbk/total_bound*100:.1f}% ({total_utbk} dari {total_bound} perangkat bound adalah UTBK-OS)")
    lines.append("")

    # Section 5: Per Server
    lines.append("## 5. Ringkasan per Server DHCP")
    lines.append("")
    if narratives.get("section5"):
        lines.append(narratives["section5"])
        lines.append("")
    lines.append("| Server | Bound | Waiting | Disabled | Total | UTBK-OS | Other |")
    lines.append("|---|---|---|---|---|---|---|")
    for server in sorted(server_data.keys()):
        d = server_data[server]
        lines.append(
            f"| {server} | {d['bound']} | {d['waiting']} | {d['disabled']} | {d['total']} | {d['utbk_os']} | {d['other']} |"
        )
    lines.append("")

    # Section 6: Non-UTBK devices
    non_utbk = [(s, d) for s, d in server_data.items() if d["other"] > 0]
    if non_utbk:
        lines.append("## 6. Perangkat Bound Non-UTBK-OS")
        lines.append("")
        for server, d in non_utbk:
            lines.append(f"### Server: {server}")
            lines.append("")
            # Find non-UTBK entries
            non_utbk_entries = []
            for e in d["entries"]:
                if "status=bound" in e and "host-name=utbk-os" not in e:
                    ip = re.search(r"address=(\S+)", e)
                    mac = re.search(r"mac-address=(\S+)", e)
                    comment = re.search(r"comment=(\S+)", e)
                    hostname = re.search(r"host-name=(\S+)", e)
                    age_m = re.search(r"age=(\S+)", e)
                    non_utbk_entries.append({
                        "ip": ip.group(1) if ip else "?",
                        "mac": mac.group(1) if mac else "-",
                        "comment": comment.group(1) if comment else "-",
                        "hostname": hostname.group(1) if hostname else "-",
                        "age": age_m.group(1) if age_m else "-",
                    })
            if non_utbk_entries:
                lines.append("| IP Address | MAC Address | Comment | Hostname | Age |")
                lines.append("|---|---|---|---|---|")
                for entry in non_utbk_entries:
                    lines.append(
                        f"| {entry['ip']} | {entry['mac']} | {entry['comment']} | {entry['hostname']} | {entry['age']} |"
                    )
                lines.append("")
        lines.append("> Perangkat non-UTBK adalah **switch infrastructure** dan perangkat lainnya.")
        lines.append("")

    # Section 7: New & Disconnected Devices
    if new_devices or disconnected_devices:
        lines.append("## 7. 📡 Perangkat Baru & Disconnect")
        lines.append("")
        if narratives.get("section7"):
            lines.append(narratives["section7"])
            lines.append("")

        if new_devices:
            lines.append(f"### 🔵 Perangkat Baru Terdeteksi ({len(new_devices)} perangkat)")
            lines.append("")
            lines.append("Perangkat yang **pertama kali terlihat** pada tanggal ini (berdasarkan MAC address).")
            lines.append("")
            lines.append("| MAC Address | IP Address | Comment | Hostname | Client ID | Status | Server |")
            lines.append("|---|---|---|---|---|---|---|")
            for dev in new_devices:
                lines.append(
                    f"| {dev['mac']} | {dev['ip']} | {dev['comment']} | {dev['hostname']} | {dev['client_id']} | {dev['status']} | {dev['server']} |"
                )
            lines.append("")

        if disconnected_devices:
            lines.append(f"### 🔴 Perangkat Disconnect ({len(disconnected_devices)} perangkat)")
            lines.append("")
            lines.append("Perangkat yang **tidak terlihat** pada tanggal ini tetapi pernah ada di hari sebelumnya.")
            lines.append("")
            lines.append("| MAC Address | Terakhir Seen | Server Terakhir |")
            lines.append("|---|---|---|")
            for dev in disconnected_devices:
                lines.append(
                    f"| {dev['mac']} | {dev['first_seen']} | {dev['server']} |"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    # Section 8: Anomalies by Router/Server
    router_anomalies = defaultdict(list)
    for anomaly in anomalies:
        for item in anomaly["data"]:
            router = item.get("server", "Unknown")
            router_anomalies[router].append({
                "type": anomaly["title"],
                "severity": anomaly["severity"],
                "emoji": anomaly["emoji"],
                "details": item,
            })

    if router_anomalies:
        lines.append("## 8. 📍 Anomali per Router")
        lines.append("")
        if narratives.get("section8"):
            lines.append(narratives["section8"])
            lines.append("")
        for router in sorted(router_anomalies.keys()):
            items = router_anomalies[router]
            lines.append(f"### {router} ({len(items)} anomali)")
            lines.append("")
            lines.append("| Status | IP | Host-name | Active-Server | Detail |")
            lines.append("|---|---|---|---|---|")
            for item in items:
                d = item["details"]
                if "Waiting" in item["type"]:
                    detail_str = f"Waiting: {d.get('time', '-')}"
                elif "Bound" in item["type"]:
                    detail_str = f"Age: {d.get('age', '-')}"
                else:
                    detail_str = item["type"]
                lines.append(
                    f"| {item['emoji']} {item['severity']} "
                    f"| {d.get('ip', '-')} "
                    f"| {d.get('hostname', '-')} "
                    f"| {d.get('server', '-')} "
                    f"| {detail_str} |"
                )
            lines.append("")

    # Section 9: Anomalies
    if anomalies:
        lines.append("## 9. ⚠️ ANOMALI TERDETEKSI")
        lines.append("")
        if narratives.get("section9"):
            lines.append(narratives["section9"])
            lines.append("")
        for i, anomaly in enumerate(anomalies, 1):
            lines.append(f"### {anomaly['emoji']} ANOMALI {i}: {anomaly['title']} ({anomaly['severity']})")
            lines.append("")
            lines.append(anomaly["description"])
            lines.append("")
            # Build header row
            header_row = "| " + " | ".join(anomaly["columns"]) + " |"
            lines.append(header_row)
            # Build separator row
            separator = "|" + "|".join(["---"] * len(anomaly["columns"])) + "|"
            lines.append(separator)
            # Build data rows
            for row in anomaly["data"]:
                vals = [str(row[k]) for k in anomaly["keys"]]
                data_row = "| " + " | ".join(vals) + " |"
                lines.append(data_row)
            lines.append("")
            lines.append(f"**Rekomendasi:** {anomaly['recommendation']}")
            lines.append("")
            lines.append("---")
            lines.append("")

    # Section 10: Recommendations
    lines.append("## 10. 📋 Ringkasan Rekomendasi")
    lines.append("")

    critical = [a for a in anomalies if a["severity"] == "CRITICAL"]
    high = [a for a in anomalies if a["severity"] == "HIGH"]
    medium = [a for a in anomalies if a["severity"] == "MEDIUM"]

    if critical:
        lines.append("### 🔴 Prioritas Tinggi")
        lines.append("| # | Anomali | Aksi |")
        lines.append("|---|---|---|")
        for i, a in enumerate(critical, 1):
            lines.append(f"| {i} | {a['title']} | {a['recommendation']} |")
        lines.append("")

    if high:
        lines.append("### 🟡 Prioritas Sedang")
        lines.append("| # | Anomali | Aksi |")
        lines.append("|---|---|---|")
        for i, a in enumerate(high, 1):
            lines.append(f"| {i} | {a['title']} | {a['recommendation']} |")
        lines.append("")

    if medium:
        lines.append("### 🟢 Prioritas Rendah")
        lines.append("| # | Anomali | Aksi |")
        lines.append("|---|---|---|")
        for i, a in enumerate(medium, 1):
            lines.append(f"| {i} | {a['title']} | {a['recommendation']} |")
        lines.append("")

    if not anomalies:
        lines.append("✅ **Tidak ada anomali terdeteksi.** Semua perangkat dalam kondisi normal.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated: {date_display}*")
    lines.append("")

    return "\n".join(lines)


def main():
    if not OUTPUT_DIR.exists():
        print(f"Error: Output directory not found: {OUTPUT_DIR}")
        sys.exit(1)

    LAPORAN_DIR.mkdir(exist_ok=True)
    force = "--force" in sys.argv

    # Group files by date
    date_files = defaultdict(list)
    for f in sorted(OUTPUT_DIR.iterdir()):
        if f.is_file() and f.name.startswith("dhcp-lease-") and f.name.endswith(".txt"):
            date = extract_date(f.name)
            if date:
                date_files[date].append(f)

    if not date_files:
        print("No dhcp-lease files found in output/ directory.")
        sys.exit(1)

    print(f"Found {len(date_files)} day(s) of data:")
    for date in sorted(date_files.keys()):
        print(f"  - {date}: {len(date_files[date])} file(s)")

    # Generate report for each day
    all_previous_data = {}
    for date in sorted(date_files.keys()):
        files = date_files[date]
        print(f"\nProcessing {date} ({len(files)} files)...")

        output_file = LAPORAN_DIR / f"dhcp-lease-{date}.md"

        # Always parse data (needed for historical trend of subsequent days)
        server_data = {}
        for f in files:
            server_name, _ = extract_server_name(f.name)
            parsed = parse_file(f)
            server_data[server_name] = parsed

        if output_file.exists() and not force:
            print(f"  -> Skipped (already exists): {output_file}")
        else:
            report = generate_report(
                date,
                server_data,
                all_previous_data if all_previous_data else None,
            )
            output_file.write_text(report, encoding="utf-8")
            print(f"  -> Generated: {output_file}")

        # Add current day to previous data for next iteration
        all_previous_data[date] = server_data

    print(f"\nDone! Reports saved to {LAPORAN_DIR}/")


if __name__ == "__main__":
    main()
