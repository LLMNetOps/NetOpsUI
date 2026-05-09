"""Tools: jalankan perintah write/destructive di router (memerlukan approval operator)."""

from __future__ import annotations

from langchain_core.tools import tool

from tools.base import validate_router, get_router_entries, ssh_creds, ssh_run_command

# Operasi yang terlalu destruktif bahkan dengan approval
_HARD_BLOCKED = [
    "format",
    "factory-reset",
    "reset-configuration",
    "export sensitive",
]


def _is_hard_blocked(command: str) -> tuple[bool, str]:
    cmd_lower = command.lower()
    for blocked in _HARD_BLOCKED:
        if blocked in cmd_lower:
            return True, blocked
    return False, ""


@tool
def run_command_write(router_name: str, command: str) -> str:
    """
    Jalankan perintah MikroTik yang memerlukan akses write di satu router.
    MEMERLUKAN APPROVAL OPERATOR sebelum dieksekusi.
    Gunakan untuk: add rule, set konfigurasi, remove entry, enable/disable service,
    reboot, dan operasi write lainnya yang tidak tercakup tool khusus.
    Contoh: '/ip/firewall/address-list/add list=blacklist address=1.2.3.4',
            '/ip/service/disable [find name=telnet]',
            '/ip/route/add dst-address=10.0.0.0/8 gateway=192.168.1.1'
    Args:
        router_name: Nama router. Gunakan list_routers() untuk daftar valid.
        command: Perintah MikroTik yang akan dieksekusi (termasuk write operations).
    """
    router_name = validate_router(router_name)
    blocked, kw = _is_hard_blocked(command)
    if blocked:
        return (
            f"Error: perintah '{kw}' diblokir permanen — terlalu destruktif. "
            f"Hubungi administrator untuk operasi ini."
        )

    entry = get_router_entries(router_name)[0]
    creds = ssh_creds()
    ok, out, err = ssh_run_command(
        host=entry["host"],
        username=creds["username"],
        password=creds["password"],
        command=command.strip(),
        port=creds["port"],
        timeout=creds["timeout"],
    )
    if not ok:
        return f"Gagal menjalankan perintah di {router_name} ({entry['host']}): {err}"

    output = out.strip() if out.strip() else "(perintah berhasil, tidak ada output)"
    header = f"Output dari {router_name} ({entry['host']}) — `{command}`\n{'─'*60}\n"
    if len(output) > 4000:
        output = output[:4000] + f"\n...[terpotong, total {len(out)} karakter]..."
    return header + output
