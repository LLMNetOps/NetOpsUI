"""Tools: kelola template dan tulis dokumen laporan."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from langchain_core.tools import tool

_BASE = Path(__file__).parent.parent
_TEMPLATES_DIR = _BASE / "skills" / "documents" / "templates"
_LAPORAN_DIR = _BASE / "laporan"
_WIB = timezone(timedelta(hours=7))


def _safe_path(base: Path, name: str) -> Path | None:
    """Return resolved path inside base, or None if path traversal detected."""
    safe_name = Path(name).name
    if not safe_name or safe_name.startswith("."):
        return None
    target = base / safe_name
    try:
        target.resolve().relative_to(base.resolve())
        return target
    except ValueError:
        return None


@tool
def list_templates() -> str:
    """
    Tampilkan daftar template laporan yang tersedia di skills/documents/templates/.
    Gunakan ini sebelum read_template() untuk mengetahui template yang tersedia.
    """
    if not _TEMPLATES_DIR.exists():
        return "Direktori templates tidak ditemukan."
    files = sorted(_TEMPLATES_DIR.glob("*.md"), key=lambda p: p.name)
    if not files:
        return "Belum ada template tersedia."
    lines = [f"Template tersedia ({len(files)} file):"]
    for f in files:
        size_kb = f.stat().st_size / 1024
        lines.append(f"  {f.name}  ({size_kb:.1f} KB)")
    return "\n".join(lines)


@tool
def read_template(name: str) -> str:
    """
    Baca isi file template dari skills/documents/templates/.
    Gunakan list_templates() terlebih dahulu untuk mengetahui nama template yang tersedia.
    Args:
        name: Nama file template (contoh: security-assessment.md, network-health.md)
    """
    if not _TEMPLATES_DIR.exists():
        return "Direktori templates tidak ditemukan."

    target = _safe_path(_TEMPLATES_DIR, name)
    if target is None:
        return "Error: nama file tidak valid."

    if not target.exists():
        available = [f.name for f in sorted(_TEMPLATES_DIR.glob("*.md"))]
        return (
            f"Template '{Path(name).name}' tidak ditemukan.\n"
            f"Template tersedia: {', '.join(available) or 'tidak ada'}"
        )

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Gagal membaca {target.name}: {e}"

    return f"=== Template: {target.name} ({len(content):,} karakter) ===\n\n{content}"


@tool
def write_document(filename: str, content: str) -> str:
    """
    Tulis dokumen laporan ke direktori laporan/ di root project.

    Konvensi penamaan: {tipe-laporan}_{YYYYMMDD}_{HHMMSS}.md
    Contoh: network-health_20260501_143022.md, security-report_20260501_090000.md

    Jika filename tidak mengandung tanggal (8 digit), timestamp WIB ditambahkan otomatis.
    Args:
        filename: Nama file output sesuai konvensi penamaan
        content:  Isi dokumen dalam format Markdown
    """
    _LAPORAN_DIR.mkdir(parents=True, exist_ok=True)

    stem = Path(filename).stem
    ts = datetime.now(_WIB).strftime("%Y%m%d_%H%M%S")

    if not re.search(r"\d{8}", stem):
        safe_name = f"{stem}_{ts}.md"
    else:
        safe_name = Path(filename).name
        if not safe_name.endswith(".md"):
            safe_name = safe_name.rsplit(".", 1)[0] + ".md"

    target = _safe_path(_LAPORAN_DIR, safe_name)
    if target is None:
        return "Error: nama file tidak valid."

    try:
        target.write_text(content, encoding="utf-8")
    except OSError as e:
        return f"Gagal menulis dokumen: {e}"

    return (
        f"Dokumen berhasil disimpan: laporan/{safe_name}\n"
        f"Ukuran: {len(content):,} karakter"
    )


@tool
def create_template(name: str, content: str) -> str:
    """
    Buat atau perbarui template laporan di skills/documents/templates/.
    Template ini dapat digunakan oleh document_agent maupun agent lain
    sebagai panduan format laporan.

    Konvensi penamaan: {tipe}-template.md atau {tipe}.md
    Contoh: incident-report.md, traffic-analysis.md, dhcp-audit.md
    Args:
        name:    Nama file template
        content: Isi template dalam format Markdown
    """
    _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = Path(name).name
    if not safe_name.endswith(".md"):
        safe_name += ".md"

    target = _safe_path(_TEMPLATES_DIR, safe_name)
    if target is None:
        return "Error: nama template tidak valid."

    action = "diperbarui" if target.exists() else "dibuat"
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as e:
        return f"Gagal menyimpan template: {e}"

    return (
        f"Template berhasil {action}: skills/documents/templates/{safe_name}\n"
        f"Ukuran: {len(content):,} karakter\n"
        f"Template ini tersedia untuk semua agent via list_templates() dan read_template()."
    )
