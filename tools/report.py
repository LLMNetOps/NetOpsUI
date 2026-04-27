"""Tools: list dan baca laporan Markdown."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from tools.base import LAPORAN_DIR


@tool
def list_reports() -> str:
    """
    Tampilkan daftar file laporan (.md) yang tersedia di direktori laporan/.
    Gunakan ini untuk mengetahui tanggal-tanggal yang tersedia
    sebelum memanggil read_report().
    """
    if not LAPORAN_DIR.exists():
        return "Direktori laporan/ tidak ditemukan."
    files = sorted(LAPORAN_DIR.glob("*.md"), key=lambda p: p.name, reverse=True)
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
    Args:
        filename: Nama file laporan (contoh: dhcp-lease-20260424.md)
                  atau 'latest' untuk laporan terbaru.
    """
    if not LAPORAN_DIR.exists():
        return "Direktori laporan/ tidak ditemukan."

    if filename.strip().lower() == "latest":
        files = sorted(LAPORAN_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return "Belum ada laporan tersedia."
        target = files[0]
    else:
        safe_name = Path(filename).name
        target = LAPORAN_DIR / safe_name
        if not target.exists():
            available = [f.name for f in sorted(LAPORAN_DIR.glob("*.md"))[-5:]]
            return (
                f"File '{safe_name}' tidak ditemukan.\n"
                f"File terbaru: {', '.join(available)}"
            )
        if not target.resolve().is_relative_to(LAPORAN_DIR.resolve()):
            return "Error: akses file di luar direktori laporan tidak diizinkan."

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Gagal membaca {target.name}: {e}"

    if len(content) > 8000:
        return (
            f"=== {target.name} (8000/{len(content)} karakter) ===\n"
            + content[:8000]
            + f"\n...[terpotong. Gunakan read_report_section() untuk bagian spesifik.]..."
        )
    return f"=== {target.name} ===\n{content}"


@tool
def read_report_section(filename: str, section: str) -> str:
    """
    Baca satu section spesifik dari laporan berdasarkan nomor atau kata kunci.
    Lebih efisien dari read_report() untuk laporan yang panjang.
    Args:
        filename: Nama file laporan atau 'latest'.
        section:  Nomor section ('7', '8', '9') atau kata kunci judul
                  ('anomali', 'utbk', 'rekomendasi', 'router', 'disconnect').
    """
    import re as _re

    if not LAPORAN_DIR.exists():
        return "Direktori laporan/ tidak ditemukan."

    if filename.strip().lower() == "latest":
        files = sorted(LAPORAN_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return "Belum ada laporan tersedia."
        target = files[0]
    else:
        safe_name = Path(filename).name
        target = LAPORAN_DIR / safe_name
        if not target.exists():
            return f"File '{safe_name}' tidak ditemukan."
        if not target.resolve().is_relative_to(LAPORAN_DIR.resolve()):
            return "Error: akses file di luar direktori laporan tidak diizinkan."

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Gagal membaca {target.name}: {e}"

    section_pattern = _re.compile(r'^(#{1,3} .+)$', _re.MULTILINE)
    matches = list(section_pattern.finditer(content))
    if not matches:
        return f"Tidak ada section ditemukan di {target.name}."

    section = section.strip()
    target_idx = None

    if section.isdigit():
        num_re = _re.compile(rf'^#{1,3} {_re.escape(section)}[\.\s]', _re.MULTILINE)
        for i, m in enumerate(matches):
            if num_re.match(content[m.start():m.end()]):
                target_idx = i
                break

    if target_idx is None:
        kw = section.lower()
        for i, m in enumerate(matches):
            if kw in content[m.start():m.end()].lower():
                target_idx = i
                break

    if target_idx is None:
        toc = [f"Section '{section}' tidak ditemukan di {target.name}.", "Section yang tersedia:"]
        for m in matches:
            heading = content[m.start():m.end()]
            if heading.startswith("## "):
                toc.append(f"  {heading}")
        return "\n".join(toc)

    start_pos = matches[target_idx].start()
    end_pos = len(content)
    heading_level = len(matches[target_idx].group().split(' ')[0])
    for j in range(target_idx + 1, len(matches)):
        next_level = len(matches[j].group().split(' ')[0])
        if next_level <= heading_level:
            end_pos = matches[j].start()
            break

    section_content = content[start_pos:end_pos].strip()
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
    Gunakan ini PERTAMA sebelum membaca section tertentu.
    Args:
        filename: Nama file laporan atau 'latest'.
    """
    import re as _re

    if not LAPORAN_DIR.exists():
        return "Direktori laporan/ tidak ditemukan."

    if filename.strip().lower() == "latest":
        files = sorted(LAPORAN_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return "Belum ada laporan tersedia."
        target = files[0]
    else:
        safe_name = Path(filename).name
        target = LAPORAN_DIR / safe_name
        if not target.exists():
            return f"File '{safe_name}' tidak ditemukan."
        if not target.resolve().is_relative_to(LAPORAN_DIR.resolve()):
            return "Error: akses file di luar direktori laporan tidak diizinkan."

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Gagal membaca {target.name}: {e}"

    headings = _re.findall(r'^(#{1,3} .+)$', content, _re.MULTILINE)
    if not headings:
        return f"Tidak ada heading ditemukan di {target.name}."

    lines = [f"Daftar isi {target.name} ({len(content):,} karakter total):"]
    for h in headings:
        level = len(h) - len(h.lstrip('#'))
        lines.append("  " * (level - 1) + h.lstrip('#').strip())
    lines.append("\nGunakan read_report_section(filename, '<nomor>') untuk membaca tiap section.")
    return "\n".join(lines)
