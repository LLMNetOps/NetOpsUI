#!/usr/bin/env python3
"""
Review CLI untuk skill yang digenerate agent — pending approval sebelum live.

Usage:
    python tests/review.py                        # list semua pending
    python tests/review.py show <name>            # tampilkan skill + checklist
    python tests/review.py approve <name>         # pindah ke production, live via hot-reload
    python tests/review.py reject <name>          # hapus dari pending
    python tests/review.py approve-all            # approve semua (hati-hati)

Workflow:
    1. Agent panggil write_skill() → skill masuk skills/.pending/
    2. Operator jalankan: python tests/review.py
    3. Buka Claude Code, minta review: "review skill pending mtu-diagnostics"
    4. Claude baca file, cek checklist, beri feedback
    5. Kalau OK: python tests/review.py approve mtu-diagnostics
    6. python tests/eval.py untuk verifikasi tidak ada regresi
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PENDING_DIR = ROOT / "skills" / ".pending"
SKILLS_DIR  = ROOT / "skills"

RESET  = "\033[0m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# Checklist yang sama dengan skill-authoring.md
_CHECKLIST = [
    ("Nama file mengikuti pola [domain]-[capability-noun]",
     lambda name, fm, body: "-" in name and not name[0].isupper()),
    ("Field 'triggers' ada dan tidak kosong",
     lambda name, fm, body: bool(fm.get("triggers"))),
    ("Field 'tools' ada (boleh kosong list)",
     lambda name, fm, body: "tools" in fm),
    ("Field 'enabled' ada",
     lambda name, fm, body: "enabled" in fm),
    ("Body punya section '## Prosedur'",
     lambda name, fm, body: "## Prosedur" in body),
    ("Ada nama tool eksplisit di body (bukan hanya 'ambil data')",
     lambda name, fm, body: any(t in body for t in (fm.get("tools") or []))),
    ("Ada contoh output atau contoh pemanggilan tool",
     lambda name, fm, body: "```" in body),
    ("Panjang skill di bawah 150 baris",
     lambda name, fm, body: body.count("\n") < 150),
    ("Tidak ada instruksi ambigu ('analisis dengan bijak', 'pertimbangkan')",
     lambda name, fm, body: "analisis dengan bijak" not in body.lower()
                             and "pertimbangkan faktor" not in body.lower()),
]


def _load_pending() -> list[Path]:
    if not PENDING_DIR.exists():
        return []
    return sorted(PENDING_DIR.rglob("*.md"))


def _parse_skill(path: Path) -> tuple[dict, str]:
    """Parse frontmatter dan body. Skip baris comment metadata di awal."""
    import yaml
    text = path.read_text(encoding="utf-8")
    # Strip generated comment
    if text.startswith("<!--"):
        text = text[text.index("-->\n") + 4:]
    if not text.strip().startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    try:
        fm = yaml.safe_load(text[3:end].strip()) or {}
    except Exception:
        fm = {}
    body = text[end + 3:].strip()
    return fm, body


def _run_checklist(name: str, fm: dict, body: str) -> list[tuple[str, bool]]:
    results = []
    for desc, fn in _CHECKLIST:
        try:
            ok = fn(name, fm, body)
        except Exception:
            ok = False
        results.append((desc, ok))
    return results


def cmd_list() -> None:
    pending = _load_pending()
    if not pending:
        print(f"{GREEN}Tidak ada skill pending review.{RESET}")
        return

    print(f"\n{BOLD}Skill pending review ({len(pending)} item):{RESET}\n")
    for p in pending:
        fm, body = _parse_skill(p)
        name = fm.get("name", p.stem)
        domain = fm.get("domain", p.parent.name)
        triggers = len(fm.get("triggers") or [])
        lines = body.count("\n")
        checks = _run_checklist(p.stem, fm, body)
        pass_count = sum(1 for _, ok in checks if ok)
        score_color = GREEN if pass_count == len(checks) else (YELLOW if pass_count >= 6 else RED)
        print(
            f"  {CYAN}{p.stem:<35}{RESET}"
            f"  domain={domain:<12}"
            f"  triggers={triggers}"
            f"  lines={lines}"
            f"  {score_color}checklist {pass_count}/{len(checks)}{RESET}"
        )

    print(f"\nJalankan: {DIM}python tests/review.py show <name>{RESET}")


def cmd_show(name: str) -> None:
    pending = _load_pending()
    matches = [p for p in pending if p.stem == name or p.stem == Path(name).stem]
    if not matches:
        print(f"{RED}Tidak ada pending skill bernama '{name}'.{RESET}", file=sys.stderr)
        print("Jalankan tanpa argumen untuk melihat daftar.")
        sys.exit(1)

    path = matches[0]
    fm, body = _parse_skill(path)
    skill_name = fm.get("name", path.stem)
    domain = fm.get("domain", path.parent.name)

    print(f"\n{BOLD}{'─' * 65}{RESET}")
    print(f"{BOLD}PENDING REVIEW: {skill_name}{RESET}  ({path.relative_to(ROOT)})")
    print(f"{BOLD}{'─' * 65}{RESET}\n")

    # Tampilkan konten penuh
    print(path.read_text(encoding="utf-8"))

    # Checklist
    print(f"\n{BOLD}{'─' * 65}{RESET}")
    print(f"{BOLD}CHECKLIST REVIEW{RESET}\n")
    checks = _run_checklist(path.stem, fm, body)
    for desc, ok in checks:
        icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {icon}  {desc}")

    pass_count = sum(1 for _, ok in checks if ok)
    total = len(checks)
    score_color = GREEN if pass_count == total else (YELLOW if pass_count >= 6 else RED)
    print(f"\n  Score: {score_color}{pass_count}/{total}{RESET}")

    print(f"\n{BOLD}{'─' * 65}{RESET}")
    print(f"Target jika diapprove: {CYAN}skills/{domain}/{path.name}{RESET}")
    print(f"\nApprove : {DIM}python tests/review.py approve {path.stem}{RESET}")
    print(f"Reject  : {DIM}python tests/review.py reject  {path.stem}{RESET}")


def cmd_approve(name: str) -> None:
    pending = _load_pending()
    matches = [p for p in pending if p.stem == name or p.stem == Path(name).stem]
    if not matches:
        print(f"{RED}Tidak ada pending skill bernama '{name}'.{RESET}", file=sys.stderr)
        sys.exit(1)

    path = matches[0]
    fm, body = _parse_skill(path)
    domain = fm.get("domain", path.parent.name)

    if domain not in {"dhcp", "routing", "monitoring", "security", "config", "documents"}:
        print(f"{RED}Domain tidak valid: '{domain}'{RESET}", file=sys.stderr)
        sys.exit(1)

    target_dir = SKILLS_DIR / domain
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name

    # Simpan tanpa baris comment metadata
    clean_content = path.read_text(encoding="utf-8")
    if clean_content.startswith("<!--"):
        clean_content = clean_content[clean_content.index("-->\n") + 4:]

    target.write_text(clean_content, encoding="utf-8")
    path.unlink()

    # Hapus domain dir jika kosong
    try:
        path.parent.rmdir()
    except OSError:
        pass

    print(f"{GREEN}✓ Approved:{RESET} skills/{domain}/{path.name}")
    print(f"  Skill langsung aktif via hot-reload.")
    print(f"\nJalankan eval untuk verifikasi:")
    print(f"  {DIM}python tests/eval.py{RESET}")


def cmd_reject(name: str) -> None:
    pending = _load_pending()
    matches = [p for p in pending if p.stem == name or p.stem == Path(name).stem]
    if not matches:
        print(f"{RED}Tidak ada pending skill bernama '{name}'.{RESET}", file=sys.stderr)
        sys.exit(1)

    path = matches[0]
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass

    print(f"{YELLOW}✗ Rejected:{RESET} {path.stem} dihapus dari pending.")


def cmd_approve_all() -> None:
    pending = _load_pending()
    if not pending:
        print("Tidak ada pending skill.")
        return
    print(f"{YELLOW}Approve {len(pending)} skill sekaligus?{RESET} [y/N] ", end="")
    if input().strip().lower() != "y":
        print("Dibatalkan.")
        return
    for p in pending:
        cmd_approve(p.stem)


def main() -> None:
    args = sys.argv[1:]

    if not args:
        cmd_list()
    elif args[0] == "show" and len(args) == 2:
        cmd_show(args[1])
    elif args[0] == "approve" and len(args) == 2:
        cmd_approve(args[1])
    elif args[0] == "reject" and len(args) == 2:
        cmd_reject(args[1])
    elif args[0] == "approve-all":
        cmd_approve_all()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
