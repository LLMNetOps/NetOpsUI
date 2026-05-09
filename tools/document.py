"""Tools: kelola template dan tulis dokumen laporan."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml
from langchain_core.tools import tool

_BASE = Path(__file__).parent.parent
_TEMPLATES_DIR = _BASE / "skills" / "documents" / "templates"
_LAPORAN_DIR = _BASE / "laporan"
_SKILLS_DIR = _BASE / "skills"
_WIB = timezone(timedelta(hours=7))

_VALID_DOMAINS = {"dhcp", "routing", "monitoring", "security", "config", "documents"}
_REQUIRED_FRONTMATTER = {"name", "domain", "triggers", "tools", "enabled"}
_PENDING_DIR = _BASE / "skills" / ".pending"


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


@tool
def write_skill(domain: str, name: str, content: str) -> str:
    """
    Tulis skill baru ke antrian review di skills/.pending/{domain}/{name}.md.
    Skill TIDAK langsung aktif — harus disetujui oleh operator via 'python tests/review.py approve'.

    File skill HARUS diawali frontmatter YAML dengan field wajib:
      name, domain, triggers (list), tools (list), enabled (bool).

    Domain yang valid: dhcp, routing, monitoring, security, config, documents

    Contoh content minimal:
      ---
      name: nama-skill
      domain: security
      triggers:
        - kata kunci pemicu
      tools:
        - audit_security
      approval_required: false
      enabled: true
      ---

      ## Konteks
      Kapan skill ini digunakan.

      ## Prosedur
      Langkah-langkah yang harus diikuti agent.

    Args:
        domain:  Domain skill (dhcp/routing/monitoring/security/config/documents)
        name:    Nama file skill tanpa ekstensi (contoh: security-audit, ospf-down)
        content: Isi lengkap file skill dalam format Markdown dengan frontmatter YAML
    """
    if domain not in _VALID_DOMAINS:
        return (
            f"Error: domain '{domain}' tidak valid.\n"
            f"Domain yang tersedia: {', '.join(sorted(_VALID_DOMAINS))}"
        )

    # Validate frontmatter
    if not content.strip().startswith("---"):
        return "Error: content harus diawali frontmatter YAML (---)"

    end = content.find("---", 3)
    if end == -1:
        return "Error: frontmatter YAML tidak tertutup (tidak ada --- penutup)"

    try:
        fm = yaml.safe_load(content[3:end].strip()) or {}
    except yaml.YAMLError as e:
        return f"Error: YAML frontmatter tidak valid — {e}"

    missing = _REQUIRED_FRONTMATTER - set(fm.keys())
    if missing:
        return f"Error: frontmatter wajib memiliki field: {', '.join(sorted(missing))}"

    if not isinstance(fm.get("triggers"), list) or not fm["triggers"]:
        return "Error: 'triggers' harus berupa list dengan minimal satu item"

    if not isinstance(fm.get("tools"), list):
        return "Error: 'tools' harus berupa list"

    # Write ke pending queue
    safe_name = Path(name).stem + ".md"
    if re.search(r'[/\\]', safe_name):
        return "Error: nama file tidak boleh mengandung path separator"

    pending_domain_dir = _PENDING_DIR / domain
    pending_domain_dir.mkdir(parents=True, exist_ok=True)

    target = pending_domain_dir / safe_name
    try:
        target.resolve().relative_to(_PENDING_DIR.resolve())
    except ValueError:
        return "Error: path traversal terdeteksi."

    # Tambah metadata review di baris pertama comment
    timestamp = datetime.now(_WIB).strftime("%Y-%m-%dT%H:%M:%S WIB")
    annotated = f"<!-- pending-review: generated {timestamp} -->\n{content}"

    try:
        target.write_text(annotated, encoding="utf-8")
    except OSError as e:
        return f"Gagal menyimpan skill ke pending: {e}"

    return (
        f"Skill '{fm['name']}' masuk antrian review: skills/.pending/{domain}/{safe_name}\n"
        f"Domain: {domain}  |  Triggers: {len(fm['triggers'])}  |  Tools: {len(fm.get('tools', []))}\n"
        f"⏳ Belum aktif — operator harus review dan approve:\n"
        f"   python tests/review.py show {safe_name[:-3]}\n"
        f"   python tests/review.py approve {safe_name[:-3]}"
    )
