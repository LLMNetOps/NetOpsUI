"""Tool: Manajemen router — add/remove/patch via data/netops.db.

Tool names, signatures, dan docstrings sama persis dengan versi YAML sebelumnya
sehingga agent definitions (netbox_agent.md, config_agent.md) tidak perlu diubah.
"""

from __future__ import annotations

from langchain_core.tools import tool

from tools.base import reload_config, validate_router, VALID_ROUTER_NAMES
from tools.db import (
    db_add_router, db_delete_router, db_update_router_field, db_get_router,
)


@tool
def patch_router_host(router_name: str, host: str) -> str:
    """
    Update field 'host' untuk router. Tidak butuh approval.
    Dipanggil otomatis oleh resolve_router_host setelah IP ditemukan via NetBox/BGP discovery.
    Setelah update, config di-reload in-memory — SSH ke router langsung bisa dilanjutkan.
    Args:
        router_name: Nama router.
        host: IP address yang akan diset sebagai host SSH.
    """
    try:
        validate_router(router_name)
        affected = db_update_router_field(router_name, "host", host)
        if affected == 0:
            return f"Router '{router_name}' tidak ditemukan di database."
        reload_config()
        return (
            f"Router diupdate.\n"
            f"  Router : {router_name}\n"
            f"  host   : {host}\n"
            f"Config di-reload — SSH ke {router_name} ({host}) sekarang aktif."
        )
    except Exception as e:
        return f"Gagal update host: {e}"


@tool
def patch_router_field(router_name: str, field: str, value: str) -> str:
    """
    Update field role, network, ros_version, atau name untuk router.
    MEMERLUKAN APPROVAL OPERATOR — perubahan mempengaruhi routing dan behavior agent.
    Args:
        router_name: Nama router.
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
        typed_value: int | str = int(value) if field == "ros_version" else value

        if field == "name":
            # Rename: insert new row, delete old — SQLite PRIMARY KEY can't be updated directly
            existing = db_get_router(router_name)
            if not existing:
                return f"Router '{router_name}' tidak ditemukan."
            db_add_router(
                name=str(typed_value),
                host=existing["host"],
                ros_version=existing["ros_version"],
                role=existing["role"],
                network=existing["network"],
                dhcp_servers=existing["dhcp_servers"],
            )
            db_delete_router(router_name)
        else:
            affected = db_update_router_field(router_name, field, typed_value)
            if affected == 0:
                return f"Router '{router_name}' tidak ditemukan di database."

        reload_config()
        return (
            f"Router diupdate.\n"
            f"  Router  : {router_name}\n"
            f"  {field:<8}: {typed_value}\n"
            f"Config di-reload — perubahan aktif."
        )
    except Exception as e:
        return f"Gagal update field: {e}"


@tool
def add_router_to_config(
    name: str,
    host: str,
    role: str,
    network: str,
    ros_version: int,
) -> str:
    """
    Tambah router baru ke database. MEMERLUKAN APPROVAL OPERATOR.
    Gunakan setelah router baru ditemukan via BGP discovery atau konfirmasi operator.
    Args:
        name: Nama unik router (contoh: GATE-IDREN-ITS).
        host: IP address management router.
        role: Role router — 'access', 'backbone', atau 'gate_idren'.
        network: Network router — 'kampus' atau 'idren'.
        ros_version: Versi RouterOS — 6 atau 7.
    """
    VALID_ROLES = {"access", "backbone", "gate_idren", "lab"}
    VALID_NETWORKS = {"kampus", "idren", "lab"}
    if role not in VALID_ROLES:
        return f"Role '{role}' tidak valid. Pilihan: {', '.join(sorted(VALID_ROLES))}."
    if network not in VALID_NETWORKS:
        return f"Network '{network}' tidak valid. Pilihan: {', '.join(sorted(VALID_NETWORKS))}."
    if ros_version not in (6, 7):
        return "ros_version harus 6 atau 7."
    try:
        if name in VALID_ROUTER_NAMES:
            return f"Router '{name}' sudah ada. Gunakan patch_router_field() untuk update."
        db_add_router(name=name, host=host, ros_version=ros_version,
                      role=role, network=network)
        reload_config()
        return (
            f"Router baru berhasil ditambahkan.\n"
            f"  name        : {name}\n"
            f"  host        : {host}\n"
            f"  role        : {role}\n"
            f"  network     : {network}\n"
            f"  ros_version : {ros_version}"
        )
    except Exception as e:
        return f"Gagal tambah router: {e}"


@tool
def remove_router_from_config(router_name: str) -> str:
    """
    Hapus router dari database. MEMERLUKAN APPROVAL OPERATOR.
    Operasi ini tidak bisa di-undo dari dalam sistem.
    Pastikan router benar-benar tidak aktif sebelum menghapus.
    Args:
        router_name: Nama router yang akan dihapus.
    """
    try:
        validate_router(router_name)
        deleted = db_delete_router(router_name)
        if deleted == 0:
            return f"Router '{router_name}' tidak ditemukan di database."
        reload_config()
        return (
            f"Router '{router_name}' dihapus dari database.\n"
            f"Config di-reload — router tidak lagi aktif di session ini."
        )
    except Exception as e:
        return f"Gagal hapus router: {e}"
