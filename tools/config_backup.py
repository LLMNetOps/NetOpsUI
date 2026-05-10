"""Tools: config backup — export, list, diff."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from tools.base import (
    validate_router, get_router_entries,
    ssh_creds, ssh_run_command, WORKDIR,
)

BACKUP_DIR = WORKDIR / "backups"
WIB = timezone(timedelta(hours=7))

_SAFE_NAME_RE = re.compile(r'^[\w\-]+$')


def _backup_path(router_name: str, timestamp: str) -> Path:
    router_dir = BACKUP_DIR / router_name
    router_dir.mkdir(parents=True, exist_ok=True)
    return router_dir / f"{timestamp}.rsc"


@tool
def backup_router_config(router_name: str) -> str:
    """
    Export dan simpan konfigurasi router ke direktori backups/.
    Menggunakan perintah /export untuk mendapat konfigurasi lengkap.
    PERHATIAN: Operasi ini memerlukan persetujuan operator sebelum dieksekusi.
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
    """
    router_name = validate_router(router_name)
    if not _SAFE_NAME_RE.match(router_name):
        return f"Error: nama router tidak valid untuk path file: '{router_name}'"

    entry = get_router_entries(router_name)[0]
    creds = ssh_creds()

    # RouterOS v6/v7 both support /export
    cmd = "/export"
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=cmd,
        port=creds["port"],
        timeout=60,
    )
    if not ok:
        return f"Gagal export config dari {router_name} ({entry['host']}): {err}"
    if not out.strip():
        return f"Export config kosong dari {router_name} — tidak ada yang disimpan."

    timestamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    path = _backup_path(router_name, timestamp)
    try:
        path.write_text(out, encoding="utf-8")
    except OSError as e:
        return f"Gagal menyimpan backup ke {path}: {e}"

    size_kb = path.stat().st_size / 1024
    lines = out.count("\n")
    return (
        f"Backup config {router_name} berhasil disimpan.\n"
        f"  File    : {path.relative_to(WORKDIR)}\n"
        f"  Ukuran  : {size_kb:.1f} KB ({lines} baris)\n"
        f"  Waktu   : {timestamp}"
    )


@tool
def list_backups(router_name: str = "") -> str:
    """
    Daftar file backup konfigurasi yang tersimpan di backups/.
    Args:
        router_name: Filter per router (opsional). Kosongkan untuk semua router.
    """
    if not BACKUP_DIR.exists():
        return "Direktori backups/ belum ada. Belum ada backup yang dibuat."

    if router_name:
        router_name = validate_router(router_name)
        dirs = [BACKUP_DIR / router_name]
    else:
        dirs = [d for d in BACKUP_DIR.iterdir() if d.is_dir()]

    if not dirs:
        return "Belum ada backup tersimpan."

    lines = [f"Backup konfigurasi tersimpan:"]
    total = 0
    for router_dir in sorted(dirs):
        files = sorted(router_dir.glob("*.rsc"), reverse=True)
        if not files:
            continue
        lines.append(f"\n  {router_dir.name}:")
        for f in files[:5]:   # show last 5 per router
            size_kb = f.stat().st_size / 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=WIB).strftime("%Y-%m-%d %H:%M")
            lines.append(f"    {f.name}  ({size_kb:.1f} KB, {mtime})")
            total += 1
        if len(files) > 5:
            lines.append(f"    ... ({len(files) - 5} file lama tidak ditampilkan)")

    if total == 0:
        return "Belum ada backup tersimpan."
    return "\n".join(lines)


@tool
def diff_config(router_name: str, file_a: str = "", file_b: str = "") -> str:
    """
    Bandingkan dua file backup konfigurasi dari router yang sama.
    Jika file_b tidak diberikan, bandingkan file_a dengan backup terbaru.
    Jika keduanya kosong, bandingkan dua backup terbaru (sebelum vs sesudah).
    Args:
        router_name: Nama router.
        file_a:      Nama file lama (contoh: 20260425_090000.rsc). Opsional.
        file_b:      Nama file baru (contoh: 20260427_143000.rsc). Opsional.
    """
    import difflib  # noqa: PLC0415

    router_name = validate_router(router_name)
    router_dir = BACKUP_DIR / router_name
    if not router_dir.exists():
        return f"Tidak ada backup untuk {router_name}."

    files_sorted = sorted(router_dir.glob("*.rsc"), key=lambda p: p.name, reverse=True)
    if len(files_sorted) < 2 and not (file_a or file_b):
        return f"Perlu minimal 2 backup untuk diff. {router_name} hanya punya {len(files_sorted)}."

    def _resolve(name: str, default_idx: int) -> Path:
        if not name:
            return files_sorted[default_idx]
        safe = Path(name).name
        p = router_dir / safe
        if not p.exists():
            raise FileNotFoundError(f"File backup '{safe}' tidak ditemukan.")
        return p

    try:
        path_a = _resolve(file_a, 1)  # older
        path_b = _resolve(file_b, 0)  # newer (most recent)
    except FileNotFoundError as e:
        return str(e)

    text_a = path_a.read_text(encoding="utf-8", errors="replace").splitlines()
    text_b = path_b.read_text(encoding="utf-8", errors="replace").splitlines()

    diff = list(difflib.unified_diff(
        text_a, text_b,
        fromfile=path_a.name,
        tofile=path_b.name,
        lineterm="",
    ))

    if not diff:
        return (
            f"Tidak ada perbedaan antara:\n"
            f"  {path_a.name}  vs  {path_b.name}\n"
            f"Konfigurasi identik."
        )

    added   = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    header = (
        f"Diff config {router_name}\n"
        f"  Lama  : {path_a.name}\n"
        f"  Baru  : {path_b.name}\n"
        f"  Δ     : +{added} baris / -{removed} baris\n"
        f"{'─'*60}\n"
    )
    diff_text = "\n".join(diff[:500])
    if len(diff) > 500:
        diff_text += f"\n...[terpotong, total {len(diff)} baris diff]"
    return header + diff_text
