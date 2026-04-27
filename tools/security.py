"""Tool: security audit — user, NTP, firewall check."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_core.tools import tool

from tools.base import (
    validate_router, get_router_entries, get_all_routers, get_router_names,
    ssh_creds, ssh_run_command,
)


def _audit_one(entry: dict[str, Any]) -> dict[str, Any]:
    """Audit satu router: user, NTP, default admin. Internal helper."""
    creds = ssh_creds()
    ros = entry["ros_version"]
    result: dict[str, Any] = {"name": entry["name"], "host": entry["host"]}

    # Users
    cmd_users = "/user/print" if ros == 7 else "user print"
    ok, out, _ = ssh_run_command(
        host=entry["host"], username=creds["username"], password=creds["password"],
        command=cmd_users, port=creds["port"], timeout=creds["timeout"],
    )
    if ok:
        result["users_raw"] = out
        result["user_count"] = out.count("name=") or out.lower().count("admin")
        result["has_default_admin"] = "admin" in out.lower()
    else:
        result["users_raw"] = ""
        result["user_count"] = 0
        result["has_default_admin"] = False

    # NTP
    cmd_ntp = "/system/ntp/client/print" if ros == 7 else "system ntp client print"
    ok, out, _ = ssh_run_command(
        host=entry["host"], username=creds["username"], password=creds["password"],
        command=cmd_ntp, port=creds["port"], timeout=creds["timeout"],
    )
    result["ntp_synced"] = ok and "synchronized: yes" in out.lower()
    result["ntp_raw"] = out if ok else ""

    return result


@tool
def audit_security(router_name: str = "all") -> str:
    """
    Audit keamanan router: cek user accounts, NTP sync, dan keberadaan
    default admin. Bisa audit satu router atau semua router sekaligus.
    Args:
        router_name: Nama router, atau 'all' untuk semua router (default).
    """
    if router_name.strip().lower() == "all":
        target_names = get_router_names()
        seen: set[str] = set()
        entries = [
            e for name in target_names
            for e in get_router_entries(name)
            if not (name in seen or seen.add(name))  # type: ignore[func-returns-value]
        ]
    else:
        router_name = validate_router(router_name)
        entries = [get_router_entries(router_name)[0]]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_audit_one, e): e for e in entries}
        for future in as_completed(futures, timeout=120):
            try:
                results.append(future.result())
            except Exception as exc:
                entry = futures[future]
                results.append({"name": entry["name"], "host": entry["host"], "error": str(exc)})

    results.sort(key=lambda x: x["name"])
    lines = ["Security Audit\n" + "═" * 60]
    issues: list[str] = []

    for r in results:
        if "error" in r:
            lines.append(f"{r['name']:<16} ✗ GAGAL: {r['error'][:60]}")
            continue
        ntp_s = "✓ synced" if r.get("ntp_synced") else "✗ NOT synced"
        adm_s = "⚠ has default 'admin'" if r.get("has_default_admin") else "✓ no default admin"
        lines.append(
            f"{r['name']:<16} NTP: {ntp_s:<14} Users: {r.get('user_count',0):>2}  {adm_s}"
        )
        if not r.get("ntp_synced"):
            issues.append(f"  [{r['name']}] NTP tidak sinkron")
        if r.get("has_default_admin"):
            issues.append(f"  [{r['name']}] User 'admin' default masih ada")

    if issues:
        lines.append("\n⚠ Temuan:\n" + "\n".join(issues))
    else:
        lines.append("\n✓ Tidak ada temuan kritis.")
    return "\n".join(lines)
