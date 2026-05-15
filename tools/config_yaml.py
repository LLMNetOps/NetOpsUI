"""Tool: Manajemen config.yaml — update router entries secara mandiri oleh agent."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import tool

from tools.base import CONFIG_FILE, reload_config, validate_router, VALID_ROUTER_NAMES


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read() -> str:
    return CONFIG_FILE.read_text(encoding="utf-8")


def _write(text: str) -> None:
    CONFIG_FILE.write_text(text, encoding="utf-8")


def _patch_field(text: str, router_name: str, field: str, value: Any) -> tuple[str, int]:
    """
    Ganti field: <value> di semua blok router yang match router_name.
    Blok dimulai dengan '  - name: X'. Field ada di indent 4 spasi.
    Return (new_text, jumlah_baris_diubah).
    """
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    in_target = False
    count = 0

    for line in lines:
        m_entry = re.match(r'^\s{2}-\s+name:\s+(\S+)', line)
        if m_entry:
            in_target = m_entry.group(1) == router_name

        if in_target:
            m_field = re.match(r'^(\s{4,})' + re.escape(field) + r':\s*.*$', line)
            if m_field:
                line = f'{m_field.group(1)}{field}: {value}\n'
                count += 1

        result.append(line)

    return ''.join(result), count


def _remove_blocks(text: str, router_name: str) -> tuple[str, int]:
    """
    Hapus semua blok router dengan nama tertentu.
    Blok berakhir ketika menemukan blok baru (  - name:) atau key top-level.
    Return (new_text, jumlah_blok_dihapus).
    """
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    skipping = False
    count = 0

    for line in lines:
        if re.match(r'^\s{2}-\s+name:\s+' + re.escape(router_name) + r'\s*$', line):
            skipping = True
            count += 1
            continue
        elif re.match(r'^\s{2}-\s+name:', line):
            skipping = False
        elif skipping and line.strip() and not re.match(r'^\s{4,}', line):
            skipping = False

        if not skipping:
            result.append(line)

    return ''.join(result), count


def _add_block(text: str, name: str, host: str, role: str, network: str, ros_version: int) -> str:
    """Sisipkan blok router baru sebelum section netbox."""
    block = (
        f"  - name: {name}\n"
        f"    host: {host}\n"
        f"    role: {role}\n"
        f"    network: {network}\n"
        f"    ros_version: {ros_version}\n"
    )
    for marker in ['\n# NetBox', '\nnetbox:']:
        idx = text.find(marker)
        if idx != -1:
            return text[:idx] + '\n' + block + text[idx:]
    return text.rstrip('\n') + '\n\n' + block


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def patch_router_host(router_name: str, host: str) -> str:
    """
    Update field 'host' untuk router di config.yaml. Tidak butuh approval.
    Dipanggil otomatis oleh resolve_router_host setelah IP ditemukan via NetBox/BGP discovery.
    Setelah update, config di-reload in-memory — SSH ke router langsung bisa dilanjutkan.
    Args:
        router_name: Nama router di config.yaml.
        host: IP address yang akan diset sebagai host SSH.
    """
    try:
        validate_router(router_name)
        text = _read()
        new_text, count = _patch_field(text, router_name, "host", host)
        if count == 0:
            return (
                f"Field 'host' tidak ditemukan di blok router '{router_name}'.\n"
                f"Router mungkin tidak punya field host — cek config.yaml manual."
            )
        _write(new_text)
        reload_config()
        return (
            f"config.yaml diupdate.\n"
            f"  Router : {router_name}\n"
            f"  host   : {host}\n"
            f"  Blok   : {count} diupdate\n"
            f"Config di-reload — SSH ke {router_name} ({host}) sekarang aktif."
        )
    except Exception as e:
        return f"Gagal update host di config.yaml: {e}"


@tool
def patch_router_field(router_name: str, field: str, value: str) -> str:
    """
    Update field role, network, ros_version, atau name untuk router di config.yaml.
    MEMERLUKAN APPROVAL OPERATOR — perubahan mempengaruhi routing dan behavior agent.
    Args:
        router_name: Nama router di config.yaml.
        field: Field yang diubah — 'role', 'network', 'ros_version', atau 'name'.
        value: Nilai baru.
    """
    ALLOWED = {"role", "network", "ros_version", "name"}
    if field not in ALLOWED:
        return f"Field '{field}' tidak diizinkan. Pilihan: {', '.join(sorted(ALLOWED))}."
    if field == "host":
        return "Gunakan patch_router_host() untuk update field 'host'."
    try:
        validate_router(router_name)
        text = _read()
        typed_value: Any = int(value) if field == "ros_version" else value
        new_text, count = _patch_field(text, router_name, field, typed_value)
        if count == 0:
            return f"Field '{field}' tidak ditemukan di blok router '{router_name}'."
        _write(new_text)
        reload_config()
        return (
            f"config.yaml diupdate.\n"
            f"  Router  : {router_name}\n"
            f"  {field:<8}: {typed_value}\n"
            f"  Blok    : {count} diupdate\n"
            f"Config di-reload — perubahan aktif."
        )
    except Exception as e:
        return f"Gagal update field di config.yaml: {e}"


@tool
def add_router_to_config(
    name: str,
    host: str,
    role: str,
    network: str,
    ros_version: int,
) -> str:
    """
    Tambah router baru ke config.yaml. MEMERLUKAN APPROVAL OPERATOR.
    Gunakan setelah router baru ditemukan via BGP discovery atau konfirmasi operator.
    Args:
        name: Nama unik router (contoh: GATE-IDREN-ITS).
        host: IP address management router.
        role: Role router — 'access', 'backbone', atau 'gate_idren'.
        network: Network router — 'kampus' atau 'idren'.
        ros_version: Versi RouterOS — 6 atau 7.
    """
    VALID_ROLES = {"access", "backbone", "gate_idren"}
    VALID_NETWORKS = {"kampus", "idren"}
    if role not in VALID_ROLES:
        return f"Role '{role}' tidak valid. Pilihan: {', '.join(sorted(VALID_ROLES))}."
    if network not in VALID_NETWORKS:
        return f"Network '{network}' tidak valid. Pilihan: {', '.join(sorted(VALID_NETWORKS))}."
    if ros_version not in (6, 7):
        return "ros_version harus 6 atau 7."
    try:
        if name in VALID_ROUTER_NAMES:
            return f"Router '{name}' sudah ada di config.yaml. Gunakan patch_router_field() untuk update."
        text = _read()
        new_text = _add_block(text, name, host, role, network, ros_version)
        _write(new_text)
        reload_config()
        return (
            f"Router baru berhasil ditambahkan ke config.yaml.\n"
            f"  name        : {name}\n"
            f"  host        : {host}\n"
            f"  role        : {role}\n"
            f"  network     : {network}\n"
            f"  ros_version : {ros_version}"
        )
    except Exception as e:
        return f"Gagal tambah router ke config.yaml: {e}"


@tool
def remove_router_from_config(router_name: str) -> str:
    """
    Hapus semua blok router dari config.yaml. MEMERLUKAN APPROVAL OPERATOR.
    Operasi ini tidak bisa di-undo dari dalam sistem.
    Pastikan router benar-benar tidak aktif sebelum menghapus.
    Args:
        router_name: Nama router yang akan dihapus dari config.yaml.
    """
    try:
        validate_router(router_name)
        text = _read()
        new_text, count = _remove_blocks(text, router_name)
        if count == 0:
            return f"Router '{router_name}' tidak ditemukan di config.yaml."
        _write(new_text)
        reload_config()
        return (
            f"Router '{router_name}' dihapus dari config.yaml.\n"
            f"  Blok dihapus : {count}\n"
            f"Config di-reload — router tidak lagi aktif di session ini."
        )
    except Exception as e:
        return f"Gagal hapus router dari config.yaml: {e}"
