"""Tool: NetBox IPAM integration — query devices, interfaces, IPs, drift detection."""

from __future__ import annotations

import re
from typing import Any

import yaml
from langchain_core.tools import tool

from tools.base import (
    CONFIG_FILE, validate_router, get_router_entries, get_unique_router_entries,
    ssh_creds, ssh_creds_for, ssh_run_command,
)


# ── NetBox client ─────────────────────────────────────────────────────────────

def _get_netbox_cfg(instance: str = "kampus") -> dict[str, Any]:
    """
    Return config dict untuk NetBox instance tertentu.
    Support format lama (single dict) dan format baru (named map).
    """
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        nb_cfg = cfg.get("netbox", {})

        # Format lama: netbox: {url: ..., token: ...}
        if "url" in nb_cfg:
            return nb_cfg

        # Format baru: netbox: {idren: {...}, kampus: {...}}
        inst_cfg = nb_cfg.get(instance)
        if not inst_cfg:
            available = list(nb_cfg.keys())
            raise ValueError(
                f"NetBox instance '{instance}' tidak ada di config.yaml.\n"
                f"Instance tersedia: {available}\n"
                f"Gunakan parameter instance='idren' atau instance='kampus'."
            )
        if not inst_cfg.get("url") or not inst_cfg.get("token"):
            raise ValueError(
                f"config.yaml[netbox.{instance}] harus memiliki url dan token."
            )
        return inst_cfg
    except FileNotFoundError:
        raise ValueError("config.yaml tidak ditemukan")


def _nb(instance: str = "kampus"):
    """Return authenticated pynetbox API client untuk instance tertentu."""
    try:
        import pynetbox
    except ImportError:
        raise ImportError("pynetbox belum terinstall. Jalankan: pip install pynetbox>=7.0")
    cfg = _get_netbox_cfg(instance)
    nb = pynetbox.api(cfg["url"], token=cfg["token"])
    if not cfg.get("ssl_verify", True):
        import requests
        s = requests.Session()
        s.verify = False
        nb.http_session = s
    return nb


def _resolve_instance(router_name: str | None, instance: str) -> str:
    """
    Resolve 'auto' ke nama instance NetBox yang tepat.
    - Dengan router_name: baca field 'network' dari config.yaml
    - Tanpa router_name atau tidak ditemukan: default 'kampus'
    """
    if instance != "auto":
        return instance
    if router_name:
        try:
            from tools.base import get_router_entries, VALID_ROUTER_NAMES
            for name in VALID_ROUTER_NAMES:
                if name.upper() == router_name.strip().upper():
                    entries = get_router_entries(name)
                    if entries:
                        return entries[0].get("network", "kampus")
        except Exception:
            pass
    return "kampus"


# ── Helpers ───────────────────────────────────────────────────────────────────

_NB_PATHS: dict[str, str] = {
    "ip-address": "ipam/ip-addresses",
    "interface": "dcim/interfaces",
    "device": "dcim/devices",
    "bgp-session": "plugins/bgp/session",
}


def _nb_url(base_url: str, obj_type: str, obj_id: int) -> str:
    """Build direct NetBox UI URL untuk object tertentu."""
    path = _NB_PATHS.get(obj_type, obj_type)
    return f"{base_url.rstrip('/')}/{path}/{obj_id}/"


def _extract_vlan_id(name: str) -> int | None:
    """Extract VLAN ID dari nama interface. Handle: vlan450-..., VLAN-702-..., vlan-450-..."""
    m = re.match(r'(?i)vlan[-_]?(\d+)', name)
    return int(m.group(1)) if m else None


def _parse_router_vlans(output: str) -> dict[tuple, dict[str, str]]:
    """
    Parse `/interface vlan print detail` → dict (vlan_id, parent) → {name, vlan_id, interface, comment}.
    Iterator-based: for each name=, find nearest vlan-id=, interface=, and preceding ;;; comment.
    """
    result: dict[tuple, dict[str, str]] = {}
    name_ms = list(re.finditer(r'name="([^"]+)"', output))
    vid_ms = list(re.finditer(r'\bvlan-id=(\d+)', output))
    iface_ms = list(re.finditer(r'\binterface=(\S+)', output))
    comment_ms = list(re.finditer(r';;;\s+(.+)', output))

    for idx, nm in enumerate(name_ms):
        pos_start = nm.start()
        pos_end = name_ms[idx + 1].start() if idx + 1 < len(name_ms) else len(output)
        prev_pos = name_ms[idx - 1].start() if idx > 0 else 0

        vid = next(
            (int(m.group(1)) for m in vid_ms if pos_start < m.start() < pos_end),
            None,
        )
        parent = next(
            (m.group(1) for m in iface_ms if pos_start < m.start() < pos_end),
            "",
        )
        comment = next(
            (m.group(1).strip() for m in comment_ms if prev_pos < m.start() < pos_start),
            "",
        )
        if vid is not None:
            result[(vid, parent)] = {
                "name": nm.group(1),
                "vlan_id": vid,
                "interface": parent,
                "comment": comment,
            }
    return result


def _parse_router_ips(output: str) -> dict[str, dict[str, str]]:
    """
    Parse `/ip address print detail` → dict address/prefix → {interface, comment}.
    Iterator-based: for each address=, find nearest interface= and preceding ;;; comment.
    """
    result: dict[str, dict[str, str]] = {}
    addr_ms = list(re.finditer(r'\baddress=(\d[\d.]+/\d+)', output))
    iface_ms = list(re.finditer(r'\binterface=(\S+)', output))
    comment_ms = list(re.finditer(r';;;\s+(.+)', output))

    for idx, am in enumerate(addr_ms):
        pos_start = am.start()
        pos_end = addr_ms[idx + 1].start() if idx + 1 < len(addr_ms) else len(output)
        prev_pos = addr_ms[idx - 1].start() if idx > 0 else 0

        iface = next(
            (m.group(1) for m in iface_ms if pos_start < m.start() < pos_end),
            "",
        )
        comment = next(
            (m.group(1).strip() for m in comment_ms if prev_pos < m.start() < pos_start),
            "",
        )
        result[am.group(1)] = {"interface": iface, "comment": comment}
    return result


def _find_nb_device_by_host(nb, router_host: str):
    """
    Cari NetBox device yang memiliki IP = router_host di antara semua IP-nya.
    Fallback dari primary_ip karena tidak semua device punya primary_ip terisi.
    """
    # 1. Try primary_ip
    for d in nb.dcim.devices.all():
        if d.primary_ip:
            if str(d.primary_ip.address).split("/")[0] == router_host:
                return d

    # 2. Fallback: search any IP address matching host
    matches = list(nb.ipam.ip_addresses.filter(address=router_host))
    if not matches:
        # Try with /24 or /32 suffix patterns
        for ip in nb.ipam.ip_addresses.all():
            if str(ip.address).split("/")[0] == router_host:
                if ip.assigned_object and ip.assigned_object_type == "dcim.interface":
                    iface_id = ip.assigned_object_id
                    iface = nb.dcim.interfaces.get(iface_id)
                    if iface:
                        return nb.dcim.devices.get(iface.device.id)
    else:
        ip = matches[0]
        if ip.assigned_object and "interface" in str(ip.assigned_object_type):
            iface = nb.dcim.interfaces.get(ip.assigned_object.id)
            if iface:
                return nb.dcim.devices.get(iface.device.id)

    return None


def _get_managed_interfaces(nb, device_name: str) -> list:
    """
    Ambil virtual interface device. Filter by tag 'managed-by-agent' jika ada,
    fallback ke semua virtual interface jika tag belum diterapkan.
    Skip loopback.
    """
    all_virtual = [
        i for i in nb.dcim.interfaces.filter(device=device_name)
        if str(i.type.value) not in ("loopback", "bridge", "lag")
        and str(i.type.value) not in ("1000base-t", "100gbase-x-qsfp28", "25gbase-x-sfp28",
                                      "10gbase-x-sfp+", "1000base-x-sfp", "other")
        and "base" not in str(i.type.value)
        and str(i.type.value) == "virtual"
    ]

    tagged = [i for i in all_virtual if any(t.slug == "managed-by-agent" for t in i.tags)]
    if tagged:
        return tagged

    # Tag belum diterapkan — pakai semua virtual interface
    return all_virtual


# ── Read tools ────────────────────────────────────────────────────────────────

@tool
def get_netbox_devices(instance: str = "kampus") -> str:
    """
    Ambil daftar semua device jaringan di NetBox beserta primary IP dan status.
    Berguna untuk melihat inventaris dan mencari nama device yang sesuai dengan router.
    Args:
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: 'kampus').
    """
    try:
        instance = _resolve_instance(None, instance)
        nb = _nb(instance)
        devices = list(nb.dcim.devices.all())
        if not devices:
            return "Tidak ada device ditemukan di NetBox."

        lines = [f"Device di NetBox [{instance}] ({len(devices)} total)", "─" * 60]
        for d in sorted(devices, key=lambda x: x.name or ""):
            name = d.name or "—"
            primary_ip = str(d.primary_ip.address) if d.primary_ip else "—"
            status = str(d.status) if d.status else "—"
            site = str(d.site) if d.site else "—"
            lines.append(
                f"  {name:<35} primary_ip={primary_ip:<22} status={status}  site={site}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mengambil devices dari NetBox: {e}"


@tool
def get_netbox_device_interfaces(device_name: str, instance: str = "auto") -> str:
    """
    Ambil daftar virtual interface device di NetBox.
    Prioritaskan interface bertag 'managed-by-agent'; jika belum ada tag, tampilkan semua virtual.
    Loopback dan interface fisik dilewati.
    Args:
        device_name: Nama device di NetBox. Gunakan get_netbox_devices() untuk daftar valid.
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto dari nama device).
    """
    try:
        instance = _resolve_instance(device_name, instance)
        nb = _nb(instance)
        interfaces = _get_managed_interfaces(nb, device_name)
        if not interfaces:
            return (
                f"Tidak ada virtual interface ditemukan untuk device '{device_name}'.\n"
                "Pastikan nama device benar dengan get_netbox_devices()."
            )

        has_tag = any(any(t.slug == "managed-by-agent" for t in i.tags) for i in interfaces)
        tag_note = "" if has_tag else " [semua virtual — tag 'managed-by-agent' belum diterapkan]"

        lines = [
            f"Interface '{device_name}'{tag_note} ({len(interfaces)} interface)",
            "─" * 60,
        ]
        for iface in sorted(interfaces, key=lambda x: x.name):
            parent = iface.parent.name if iface.parent else "—"
            status = "enabled" if iface.enabled else "DISABLED"
            desc = iface.description or "—"
            vlan_id = _extract_vlan_id(iface.name)

            ips = list(nb.ipam.ip_addresses.filter(interface_id=iface.id))
            ip_list = ", ".join(str(ip.address) for ip in ips) if ips else "—"

            lines.append(
                f"\n  {iface.name}\n"
                f"    vlan-id={vlan_id or '?'}  parent={parent}  {status}\n"
                f"    desc={desc}\n"
                f"    IPs: {ip_list}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mengambil interfaces dari NetBox: {e}"


@tool
def get_netbox_device_ips(device_name: str, instance: str = "auto") -> str:
    """
    Ambil semua IP address yang di-assign ke device di NetBox.
    Args:
        device_name: Nama device di NetBox. Gunakan get_netbox_devices() untuk daftar valid.
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto).
    """
    try:
        instance = _resolve_instance(device_name, instance)
        nb = _nb(instance)
        ips = list(nb.ipam.ip_addresses.filter(device=device_name))
        if not ips:
            return f"Tidak ada IP address ditemukan untuk device '{device_name}' di NetBox."

        lines = [f"IP Addresses '{device_name}' ({len(ips)} total)", "─" * 60]
        for ip in sorted(ips, key=lambda x: str(x.address)):
            interface = ip.assigned_object.name if ip.assigned_object else "—"
            status = str(ip.status)
            desc = ip.description or "—"
            lines.append(
                f"  {str(ip.address):<25} interface={str(interface):<45} status={status}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mengambil IP addresses dari NetBox: {e}"


@tool
def get_netbox_drift_report(router_name: str, device_name: str = "", instance: str = "auto") -> str:
    """
    Bandingkan konfigurasi interface VLAN dan IP di NetBox vs kondisi aktual router MikroTik.
    Matching interface: berdasarkan VLAN ID (bukan nama — nama bisa berbeda antara NetBox dan router).
    Matching device: cari device NetBox yang punya IP = host router di config.yaml.
    Args:
        router_name: Nama router di config.yaml. Gunakan list_routers() untuk daftar valid.
        device_name: (opsional) Nama device di NetBox jika auto-matching gagal.
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto dari network router).
    """
    try:
        router_name = validate_router(router_name)
        entry = get_router_entries(router_name)[0]
        creds = ssh_creds_for(entry)
        router_host = entry["host"]
        ros = entry["ros_version"]
        instance = _resolve_instance(router_name, instance)

        nb = _nb(instance)

        # Find NetBox device
        if device_name:
            nb_device = nb.dcim.devices.get(name=device_name)
            if not nb_device:
                return f"Device '{device_name}' tidak ditemukan di NetBox."
        else:
            nb_device = _find_nb_device_by_host(nb, router_host)
            if not nb_device:
                return (
                    f"Router '{router_name}' (host={router_host}) tidak cocok dengan device manapun di NetBox.\n"
                    f"Gunakan parameter device_name=<nama> untuk menentukan device secara manual.\n"
                    f"Jalankan get_netbox_devices() untuk daftar nama device."
                )

        # NetBox: virtual interfaces
        nb_interfaces = _get_managed_interfaces(nb, nb_device.name)
        nb_iface_by_vid: dict[tuple, Any] = {}
        for i in nb_interfaces:
            vid = _extract_vlan_id(i.name)
            parent = i.parent.name if i.parent else ""
            if vid is not None:
                nb_iface_by_vid[(vid, parent)] = i

        # NetBox: IPs
        nb_ips = list(nb.ipam.ip_addresses.filter(device=nb_device.name))
        nb_ip_set = {str(ip.address) for ip in nb_ips}

        # SSH: VLAN interfaces
        vlan_cmd = "/interface/vlan/print detail" if ros == 7 else "interface vlan print detail"
        ip_cmd = "/ip/address/print detail" if ros == 7 else "ip address print detail"

        ok_vlan, out_vlan, err_vlan = ssh_run_command(
            host=router_host, username=creds["username"], password=creds["password"],
            command=vlan_cmd, port=creds["port"], timeout=creds["timeout"],
        )
        ok_ip, out_ip, err_ip = ssh_run_command(
            host=router_host, username=creds["username"], password=creds["password"],
            command=ip_cmd, port=creds["port"], timeout=creds["timeout"],
        )

        if not ok_vlan:
            return f"Gagal ambil VLAN interfaces dari router: {err_vlan}"
        if not ok_ip:
            return f"Gagal ambil IP addresses dari router: {err_ip}"

        router_vlan_map = _parse_router_vlans(out_vlan)   # {(vid, parent): {name, ...}}
        router_ip_map = _parse_router_ips(out_ip)          # {address/prefix: {interface, comment}}

        # Build report
        has_tag = any(any(t.slug == "managed-by-agent" for t in i.tags) for i in nb_interfaces)
        tag_note = "" if has_tag else "\n[!] Tag 'managed-by-agent' belum ada — membandingkan semua virtual interface"

        lines = [
            f"Drift Report: {router_name} ({router_host}) ↔ NetBox '{nb_device.name}'",
            "═" * 70,
            tag_note,
        ]

        # Interface drift (by VLAN ID + parent)
        nb_keys = set(nb_iface_by_vid.keys())
        router_keys = set(router_vlan_map.keys())
        missing_in_router = nb_keys - router_keys
        extra_in_router = router_keys - nb_keys

        lines.append(
            f"\n[INTERFACE VLAN] NetBox: {len(nb_keys)}  |  Router: {len(router_keys)}"
        )

        if missing_in_router:
            lines.append(f"\n  PERLU DIBUAT DI ROUTER ({len(missing_in_router)}):")
            for (vid, parent) in sorted(missing_in_router):
                iface = nb_iface_by_vid[(vid, parent)]
                desc = iface.description or ""
                nb_name = iface.name
                lines.append(
                    f"    + vlan-id={vid}  parent={parent or '?'}  nama-netbox={nb_name}  desc={desc}\n"
                    f"      → /interface/vlan/add name=\"{nb_name}\" vlan-id={vid} "
                    f"interface={parent} comment=\"{desc}\""
                )
        else:
            lines.append("  Semua VLAN interface NetBox sudah ada di router (by VLAN ID). ✓")

        if extra_in_router:
            lines.append(f"\n  ADA DI ROUTER, TIDAK DI NETBOX ({len(extra_in_router)}) [informasi]:")
            for (vid, parent) in sorted(extra_in_router):
                info = router_vlan_map[(vid, parent)]
                lines.append(f"    ? vlan-id={vid}  parent={parent}  nama-router={info['name']}")

        # IP drift
        router_ip_set = set(router_ip_map.keys())
        missing_ip_in_router = nb_ip_set - router_ip_set
        extra_ip_in_router = router_ip_set - nb_ip_set


        lines.append(f"\n[IP ADDRESS] NetBox: {len(nb_ip_set)}  |  Router: {len(router_ip_set)}")

        if missing_ip_in_router:
            lines.append(f"\n  IP PERLU DITAMBAH DI ROUTER ({len(missing_ip_in_router)}):")
            for ip in sorted(missing_ip_in_router):
                nb_ip_obj = next((i for i in nb_ips if str(i.address) == ip), None)
                iface_name = nb_ip_obj.assigned_object.name if (nb_ip_obj and nb_ip_obj.assigned_object) else "?"
                lines.append(
                    f"    + {ip}  interface={iface_name}\n"
                    f"      → /ip/address/add address={ip} interface={iface_name}"
                )
        else:
            lines.append("  Semua IP NetBox sudah ada di router. ✓")

        if extra_ip_in_router:
            lines.append(f"\n  IP ADA DI ROUTER, TIDAK DI NETBOX ({len(extra_ip_in_router)}) [informasi]:")
            for ip in sorted(extra_ip_in_router):
                lines.append(f"    ? {ip}  interface={router_ip_map[ip]['interface']}")

        # Summary
        total_drift = len(missing_in_router) + len(missing_ip_in_router)
        lines.append(f"\n{'═' * 70}")
        if total_drift == 0:
            lines.append("HASIL: Tidak ada drift. Router sinkron dengan NetBox. ✓")
        else:
            lines.append(
                f"HASIL: {total_drift} item perlu disinkronisasi ke router "
                f"({len(missing_in_router)} interface, {len(missing_ip_in_router)} IP)."
            )
            lines.append("Handoff ke config_agent untuk eksekusi dengan approval operator.")

        return "\n".join(lines)

    except Exception as e:
        return f"Gagal menjalankan drift report: {e}"


# ── VLAN provisioning tools ───────────────────────────────────────────────────

@tool
def get_netbox_vlan_groups(instance: str = "idren") -> str:
    """
    Ambil daftar VLAN group di NetBox beserta range VLAN ID, breakdown status (active/reserved),
    dan slot yang benar-benar kosong (belum ada di NetBox sama sekali).
    Gunakan untuk memilih group yang tepat saat provisioning VLAN baru (per ISP atau tipe koneksi).
    Args:
        instance: Instance NetBox — 'idren' atau 'kampus' (default: 'idren' — VLAN groups ada di IDREN).
    """
    try:
        instance = _resolve_instance(None, instance)
        nb = _nb(instance)
        groups = list(nb.ipam.vlan_groups.all())
        if not groups:
            return "Tidak ada VLAN group ditemukan di NetBox."

        lines = [f"VLAN Groups di NetBox [{instance}] ({len(groups)} group)", "─" * 75]
        for g in sorted(groups, key=lambda x: x.min_vid):
            vlans = list(nb.ipam.vlans.filter(group=g.slug))
            active = sum(1 for v in vlans if str(v.status.value) == "active")
            reserved = sum(1 for v in vlans if str(v.status.value) == "reserved")
            total_range = g.max_vid - g.min_vid + 1
            empty = total_range - len(vlans)  # ID belum ada di NetBox sama sekali
            lines.append(
                f"  {g.name:<30} slug={g.slug:<20} range={g.min_vid}-{g.max_vid}  "
                f"active={active}  reserved={reserved}  kosong={empty}"
            )
        lines.append(
            "\nKeterangan: 'kosong' = ID belum ada di NetBox (langsung bisa dipakai). "
            "'reserved' = ada di NetBox tapi belum aktif — bisa diubah manual ke 'active'."
        )
        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mengambil VLAN groups dari NetBox: {e}"


@tool
def get_next_available_vlan(group_slug: str, instance: str = "idren") -> str:
    """
    Cari VLAN ID berikutnya yang tersedia dalam VLAN group tertentu di NetBox.
    Prioritas: ID yang benar-benar kosong (belum ada di NetBox) — bukan yang berstatus reserved.
    Jika tidak ada slot kosong tapi ada reserved, laporkan reserved sebagai alternatif.
    Args:
        group_slug: Slug VLAN group (contoh: 'vg-cbn', 'vg-telkom'). Lihat get_netbox_vlan_groups().
        instance: Instance NetBox — 'idren' atau 'kampus' (default: 'idren').
    """
    try:
        instance = _resolve_instance(None, instance)
        nb = _nb(instance)
        group = nb.ipam.vlan_groups.get(slug=group_slug)
        if not group:
            return (
                f"VLAN group '{group_slug}' tidak ditemukan di NetBox.\n"
                f"Jalankan get_netbox_vlan_groups() untuk daftar slug yang valid."
            )

        vlans = list(nb.ipam.vlans.filter(group=group_slug))
        all_vids = {v.vid: str(v.status.value) for v in vlans}
        active_vids = {vid for vid, s in all_vids.items() if s == "active"}
        reserved_vids = sorted(vid for vid, s in all_vids.items() if s == "reserved")

        empty_vids = [
            vid for vid in range(group.min_vid, group.max_vid + 1)
            if vid not in all_vids
        ]

        lines = [
            f"VLAN Group: {group.name} (slug={group_slug})",
            f"Range     : {group.min_vid}–{group.max_vid}  "
            f"(total {group.max_vid - group.min_vid + 1} slot)",
            f"Active    : {len(active_vids)}",
            f"Reserved  : {len(reserved_vids)}",
            f"Kosong    : {len(empty_vids)}",
        ]

        if empty_vids:
            next_vid = empty_vids[0]
            lines.append(f"\nNext ID (kosong): {next_vid}  → nama interface: vlan{next_vid}")
        elif reserved_vids:
            lines.append(
                f"\nTidak ada slot kosong. Tapi ada {len(reserved_vids)} VLAN berstatus 'reserved'."
                f"\nID reserved pertama: {reserved_vids[0]}  → bisa diubah ke 'active' di NetBox UI,"
                f"\n  lalu gunakan vlan{reserved_vids[0]} untuk interface baru."
                f"\n\nUntuk lihat semua reserved: get_netbox_vlan_group_detail('{group_slug}')"
            )
        else:
            lines.append(
                f"\nGroup penuh — semua {group.max_vid - group.min_vid + 1} slot active."
                f"\nPerluas range di NetBox UI atau gunakan group lain."
            )

        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mencari VLAN tersedia: {e}"


@tool
def get_netbox_vlan_group_detail(group_slug: str, instance: str = "idren") -> str:
    """
    Tampilkan semua VLAN dalam satu group beserta status dan deskripsi masing-masing.
    Berguna untuk melihat VLAN mana yang berstatus 'reserved' dan bisa diubah ke 'active'.
    Args:
        group_slug: Slug VLAN group. Lihat get_netbox_vlan_groups() untuk daftar slug.
        instance: Instance NetBox — 'idren' atau 'kampus' (default: 'idren').
    """
    try:
        instance = _resolve_instance(None, instance)
        nb = _nb(instance)
        group = nb.ipam.vlan_groups.get(slug=group_slug)
        if not group:
            return (
                f"VLAN group '{group_slug}' tidak ditemukan.\n"
                f"Jalankan get_netbox_vlan_groups() untuk daftar slug yang valid."
            )

        vlans = sorted(nb.ipam.vlans.filter(group=group_slug), key=lambda v: v.vid)
        total_range = group.max_vid - group.min_vid + 1
        used_vids = {v.vid for v in vlans}
        empty_count = total_range - len(vlans)

        lines = [
            f"Detail VLAN Group: {group.name} (slug={group_slug})",
            f"Range: {group.min_vid}–{group.max_vid}  |  "
            f"Total: {len(vlans)} VLAN  |  Kosong: {empty_count} slot",
            "─" * 70,
        ]

        if not vlans:
            lines.append("  (kosong — belum ada VLAN di group ini)")
        else:
            for v in vlans:
                status = str(v.status.value)
                status_icon = "✓" if status == "active" else "○" if status == "reserved" else "?"
                desc = v.description or v.name or "—"
                lines.append(f"  {status_icon} {v.vid:<6} [{status:<8}]  {desc}")

        lines.append(
            f"\nLegenda: ✓ active  ○ reserved  ? lainnya"
            f"\nUntuk ubah status reserved → active: buka NetBox UI → IPAM → VLANs → edit."
        )
        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mengambil detail VLAN group: {e}"


@tool
def create_netbox_vlan_interface(
    device_name: str,
    vlan_id: int,
    parent_interface: str,
    description: str,
    instance: str = "auto",
) -> str:
    """
    Buat VLAN interface baru di NetBox untuk device tertentu. MEMERLUKAN APPROVAL OPERATOR.
    Interface dibuat dengan nama standar vlan<ID> (contoh: vlan450, vlan702).
    Gunakan setelah get_next_available_vlan() mengkonfirmasi VLAN ID tersedia.
    Args:
        device_name: Nama device di NetBox. Gunakan get_netbox_devices() untuk daftar valid.
        vlan_id: VLAN ID (integer). Nama interface otomatis: vlan<vlan_id>.
        parent_interface: Nama interface parent fisik di NetBox (contoh: ether1, sfp-sfpplus1).
        description: Deskripsi interface. Format standar:
            - Link IDREN  : 'TO GATE-IDREN-<DEST> VIA <ISP>'
            - ISP uplink  : 'UPLINK VIA <ISP>'
            - Server      : 'SRV <fungsi>'
            - Peering     : 'TO <DEST> VIA FIBER'
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto).
    """
    try:
        instance = _resolve_instance(device_name, instance)
        cfg = _get_netbox_cfg(instance)
        nb = _nb(instance)

        device = nb.dcim.devices.get(name=device_name)
        if not device:
            return f"Device '{device_name}' tidak ditemukan di NetBox."

        interface_name = f"vlan{vlan_id}"

        # Check if already exists
        existing = list(nb.dcim.interfaces.filter(device=device_name, name=interface_name))
        if existing:
            return (
                f"Interface '{interface_name}' sudah ada di NetBox untuk device '{device_name}'.\n"
                f"Gunakan update_netbox_interface() untuk memperbarui, bukan membuat baru."
            )

        # Resolve parent interface
        parent = list(nb.dcim.interfaces.filter(device=device_name, name=parent_interface))
        if not parent:
            return (
                f"Parent interface '{parent_interface}' tidak ditemukan untuk device '{device_name}'.\n"
                f"Jalankan get_netbox_device_interfaces('{device_name}') untuk daftar interface."
            )
        parent_id = parent[0].id

        payload: dict[str, Any] = {
            "device": device.id,
            "name": interface_name,
            "type": "virtual",
            "parent": parent_id,
            "description": description,
            "enabled": True,
        }

        result = nb.dcim.interfaces.create(**payload)
        return (
            f"Interface berhasil dibuat di NetBox.\n"
            f"  Device     : {device_name}\n"
            f"  Interface  : {interface_name}\n"
            f"  Parent     : {parent_interface}\n"
            f"  VLAN ID    : {vlan_id}\n"
            f"  Deskripsi  : {description}\n"
            f"  NetBox     : {_nb_url(cfg['url'], 'interface', result.id)}\n"
            f"\nLangkah berikutnya: add_netbox_ip_address() untuk assign IP ke interface ini."
        )
    except Exception as e:
        return f"Gagal membuat interface di NetBox: {e}"


# ── Write tools (approval required via netbox_agent definition) ───────────────

@tool
def add_netbox_ip_address(
    ip_with_prefix: str,
    interface_name: str,
    device_name: str,
    description: str = "",
    instance: str = "auto",
) -> str:
    """
    Tambahkan IP address ke interface device di NetBox. MEMERLUKAN APPROVAL OPERATOR.
    Gunakan saat IP baru perlu didokumentasikan di NetBox sebagai source of truth.
    Args:
        ip_with_prefix: IP dengan prefix notation (contoh: 192.168.10.1/24)
        interface_name: Nama interface di NetBox. Gunakan get_netbox_device_interfaces().
        device_name: Nama device di NetBox. Gunakan get_netbox_devices().
        description: Deskripsi IP (opsional)
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto).
    """
    try:
        instance = _resolve_instance(device_name, instance)
        cfg = _get_netbox_cfg(instance)
        nb = _nb(instance)
        interfaces = list(nb.dcim.interfaces.filter(device=device_name, name=interface_name))
        if not interfaces:
            return f"Interface '{interface_name}' tidak ditemukan untuk device '{device_name}' di NetBox."
        iface = interfaces[0]

        # Duplicate check: same address + same interface
        existing = list(nb.ipam.ip_addresses.filter(address=ip_with_prefix, interface_id=iface.id))
        if existing:
            ex = existing[0]
            return (
                f"IP '{ip_with_prefix}' sudah terdaftar di NetBox — tidak dibuat ulang.\n"
                f"  Device    : {device_name}\n"
                f"  Interface : {interface_name}\n"
                f"  Status    : {ex.status}\n"
                f"  Deskripsi : {ex.description or '(kosong)'}\n"
                f"  NetBox    : {_nb_url(cfg['url'], 'ip-address', ex.id)}\n"
                f"Gunakan update_netbox_interface() jika perlu ubah deskripsi."
            )

        payload: dict[str, Any] = {
            "address": ip_with_prefix,
            "assigned_object_type": "dcim.interface",
            "assigned_object_id": iface.id,
            "status": "active",
        }
        if description:
            payload["description"] = description

        result = nb.ipam.ip_addresses.create(**payload)
        return (
            f"IP address berhasil ditambahkan di NetBox.\n"
            f"  Device    : {device_name}\n"
            f"  Interface : {interface_name}\n"
            f"  Address   : {result.address}\n"
            f"  Status    : {result.status}\n"
            f"  Deskripsi : {result.description or '(kosong)'}\n"
            f"  NetBox    : {_nb_url(cfg['url'], 'ip-address', result.id)}"
        )
    except Exception as e:
        return f"Gagal menambahkan IP address ke NetBox: {e}"


@tool
def update_netbox_interface(
    interface_name: str,
    device_name: str,
    description: str | None = None,
    enabled: bool | None = None,
    instance: str = "auto",
) -> str:
    """
    Update properties interface di NetBox. MEMERLUKAN APPROVAL OPERATOR.
    Minimal satu dari description atau enabled harus diisi.
    Args:
        interface_name: Nama interface di NetBox
        device_name: Nama device di NetBox. Gunakan get_netbox_devices().
        description: Deskripsi baru interface (opsional)
        enabled: Status interface — True=enabled, False=disabled (opsional)
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto).
    """
    try:
        instance = _resolve_instance(device_name, instance)
        cfg = _get_netbox_cfg(instance)
        nb = _nb(instance)
        interfaces = list(nb.dcim.interfaces.filter(device=device_name, name=interface_name))
        if not interfaces:
            return f"Interface '{interface_name}' tidak ditemukan untuk device '{device_name}' di NetBox."
        iface = interfaces[0]

        updates: dict[str, Any] = {}
        if description is not None:
            updates["description"] = description
        if enabled is not None:
            updates["enabled"] = enabled

        if not updates:
            return "Tidak ada perubahan. Isi minimal satu dari: description, enabled."

        iface.update(updates)
        changed = ", ".join(f"{k}={v}" for k, v in updates.items())
        return (
            f"Interface berhasil diupdate di NetBox.\n"
            f"  Device    : {device_name}\n"
            f"  Interface : {interface_name}\n"
            f"  Perubahan : {changed}\n"
            f"  NetBox    : {_nb_url(cfg['url'], 'interface', iface.id)}"
        )
    except Exception as e:
        return f"Gagal update interface di NetBox: {e}"


@tool
def populate_netbox_from_router(
    router_name: str,
    device_name: str = "",
    dry_run: bool = True,
    instance: str = "auto",
) -> str:
    """
    Populate NetBox dengan data VLAN interface dan IP address dari router MikroTik.
    Gunakan saat NetBox belum lengkap dan router adalah ground truth saat ini.

    Yang dilakukan:
    - Fix parent interface yang salah di NetBox (data router lebih akurat)
    - Tambah VLAN interface yang ada di router tapi belum di NetBox (tanpa tag)
    - Tambah IP address yang ada di router tapi belum di NetBox
    - Konflik prefix IP (alamat sama, prefix beda): dilaporkan, tidak diubah

    dry_run=True (default): hanya tampilkan rencana tanpa mengubah NetBox.
    dry_run=False: eksekusi perubahan ke NetBox. MEMERLUKAN APPROVAL OPERATOR.

    Args:
        router_name: Nama router di config.yaml. Gunakan list_routers() untuk daftar valid.
        device_name: Nama device di NetBox. Wajib jika auto-match gagal.
        dry_run: True=simulasi saja, False=eksekusi. Default True.
        instance: Instance NetBox — 'idren', 'kampus', atau 'auto' (default: auto dari network router).
    """
    try:
        router_name = validate_router(router_name)
        entry = get_router_entries(router_name)[0]
        creds = ssh_creds_for(entry)
        router_host = entry["host"]
        ros = entry["ros_version"]
        instance = _resolve_instance(router_name, instance)

        nb = _nb(instance)

        # Find NetBox device
        if device_name:
            nb_device = nb.dcim.devices.get(name=device_name)
            if not nb_device:
                return f"Device '{device_name}' tidak ditemukan di NetBox."
        else:
            nb_device = _find_nb_device_by_host(nb, router_host)
            if not nb_device:
                return (
                    f"Auto-match gagal untuk router '{router_name}' (host={router_host}).\n"
                    f"Gunakan parameter device_name=<nama>."
                )

        # SSH: get router data
        vlan_cmd = "/interface/vlan/print detail" if ros == 7 else "interface vlan print detail"
        ip_cmd = "/ip/address/print detail" if ros == 7 else "ip address print detail"

        ok_vlan, out_vlan, err_vlan = ssh_run_command(
            host=router_host, username=creds["username"], password=creds["password"],
            command=vlan_cmd, port=creds["port"], timeout=creds["timeout"],
        )
        ok_ip, out_ip, err_ip = ssh_run_command(
            host=router_host, username=creds["username"], password=creds["password"],
            command=ip_cmd, port=creds["port"], timeout=creds["timeout"],
        )
        if not ok_vlan:
            return f"Gagal SSH VLAN: {err_vlan}"
        if not ok_ip:
            return f"Gagal SSH IP: {err_ip}"

        router_vlans = _parse_router_vlans(out_vlan)   # {(vid, parent): {name, comment, ...}}
        router_ips = _parse_router_ips(out_ip)          # {addr/pfx: {interface, comment}}

        # NetBox: existing state
        nb_all_ifaces = list(nb.dcim.interfaces.filter(device=nb_device.name))
        nb_iface_by_name: dict[str, Any] = {i.name: i for i in nb_all_ifaces}
        nb_physical: dict[str, Any] = {
            i.name: i for i in nb_all_ifaces
            if str(i.type.value) not in ("virtual", "bridge", "lag")
        }
        nb_virtual_by_vid: dict[tuple, Any] = {}
        for i in nb_all_ifaces:
            if str(i.type.value) == "virtual":
                vid = _extract_vlan_id(i.name)
                parent_name = i.parent.name if i.parent else ""
                if vid is not None:
                    nb_virtual_by_vid[(vid, parent_name)] = i

        nb_ips_list = list(nb.ipam.ip_addresses.filter(device=nb_device.name))
        nb_ip_by_addr: dict[str, Any] = {str(ip.address): ip for ip in nb_ips_list}

        # ── Plan ─────────────────────────────────────────────────────────────────

        fixes: list[dict] = []        # parent mismatch fixes
        new_ifaces: list[dict] = []   # VLAN interfaces to create
        new_ips: list[dict] = []      # IPs to create
        ip_conflicts: list[dict] = [] # same address, different prefix

        # 1. Fix parent mismatch for existing NetBox virtual interfaces
        for (vid, parent_name), nb_iface in nb_virtual_by_vid.items():
            router_iface = router_vlans.get((vid, parent_name))
            if router_iface:
                continue  # parent matches
            # Try find this vid with any parent in router
            router_match = next(
                ((v, p) for (v, p) in router_vlans if v == vid),
                None,
            )
            if router_match:
                correct_parent = router_vlans[router_match]["interface"]
                if correct_parent != parent_name:
                    fixes.append({
                        "iface_name": nb_iface.name,
                        "old_parent": parent_name,
                        "new_parent": correct_parent,
                        "nb_iface": nb_iface,
                    })

        # 2. New VLAN interfaces: in router, not in NetBox (by vid + parent)
        for (vid, parent), data in router_vlans.items():
            if (vid, parent) not in nb_virtual_by_vid:
                parent_obj = nb_physical.get(parent)
                new_ifaces.append({
                    "name": data["name"],
                    "vlan_id": vid,
                    "parent": parent,
                    "parent_id": parent_obj.id if parent_obj else None,
                    "comment": data.get("comment", ""),
                })

        # 3. IP addresses: in router, not in NetBox
        for addr, ip_data in router_ips.items():
            addr_only = addr.split("/")[0]
            if addr in nb_ip_by_addr:
                continue  # exact match, skip
            # Check same address, different prefix
            conflict = next(
                (nb_addr for nb_addr in nb_ip_by_addr if nb_addr.split("/")[0] == addr_only),
                None,
            )
            if conflict:
                ip_conflicts.append({
                    "router_addr": addr,
                    "netbox_addr": conflict,
                    "interface": ip_data["interface"],
                })
                continue
            # Find interface in NetBox (may be newly created — handle by name)
            iface_name = ip_data["interface"]
            nb_iface_obj = nb_iface_by_name.get(iface_name)
            new_ips.append({
                "address": addr,
                "interface": iface_name,
                "nb_iface": nb_iface_obj,  # None jika interface baru (belum dibuat)
                "comment": ip_data.get("comment", ""),
            })

        # ── Report / Execute ──────────────────────────────────────────────────────

        mode = "DRY-RUN" if dry_run else "EKSEKUSI"
        lines = [
            f"Populate NetBox dari Router: {router_name} → '{nb_device.name}' [{mode}]",
            "═" * 70,
        ]

        # Fixes
        lines.append(f"\n[FIX PARENT] {len(fixes)} interface perlu diperbaiki:")
        if fixes:
            for f in fixes:
                lines.append(
                    f"  {f['iface_name']}: parent {f['old_parent'] or '(kosong)'} → {f['new_parent']}"
                )
                if not dry_run:
                    new_parent_obj = nb_physical.get(f["new_parent"])
                    if new_parent_obj:
                        f["nb_iface"].update({"parent": new_parent_obj.id})
                        lines[-1] += " ✓"
                    else:
                        lines[-1] += f" ✗ (parent '{f['new_parent']}' tidak ada di NetBox)"
        else:
            lines.append("  Tidak ada.")

        # New interfaces
        lines.append(f"\n[INTERFACE BARU] {len(new_ifaces)} VLAN interface akan dibuat:")
        created_iface_ids: dict[str, int] = {}
        if new_ifaces:
            for ni in sorted(new_ifaces, key=lambda x: x["vlan_id"]):
                parent_note = ni["parent"] if ni["parent_id"] else f"{ni['parent']} (parent tidak ada di NetBox!)"
                lines.append(
                    f"  vlan-id={ni['vlan_id']}  name={ni['name']}  parent={parent_note}"
                )
                if not dry_run:
                    payload: dict[str, Any] = {
                        "device": nb_device.id,
                        "name": ni["name"],
                        "type": "virtual",
                        "description": ni["comment"],
                    }
                    if ni["parent_id"]:
                        payload["parent"] = ni["parent_id"]
                    try:
                        created = nb.dcim.interfaces.create(**payload)
                        created_iface_ids[ni["name"]] = created.id
                        lines[-1] += " ✓"
                    except Exception as ex:
                        lines[-1] += f" ✗ ({ex})"
        else:
            lines.append("  Tidak ada.")

        # New IPs
        lines.append(f"\n[IP BARU] {len(new_ips)} IP address akan ditambah:")
        if new_ips:
            for ni in sorted(new_ips, key=lambda x: x["address"]):
                iface_note = ni["interface"]
                lines.append(f"  {ni['address']}  interface={iface_note}")
                if not dry_run:
                    # Resolve interface ID (existing or newly created)
                    iface_id = None
                    if ni["nb_iface"]:
                        iface_id = ni["nb_iface"].id
                    elif ni["interface"] in created_iface_ids:
                        iface_id = created_iface_ids[ni["interface"]]
                    else:
                        # Try fetch freshly created interface
                        fresh = list(nb.dcim.interfaces.filter(
                            device=nb_device.name, name=ni["interface"]
                        ))
                        if fresh:
                            iface_id = fresh[0].id

                    if iface_id is None:
                        lines[-1] += f" ✗ (interface '{ni['interface']}' tidak ditemukan)"
                        continue
                    try:
                        payload = {
                            "address": ni["address"],
                            "assigned_object_type": "dcim.interface",
                            "assigned_object_id": iface_id,
                            "status": "active",
                        }
                        if ni["comment"]:
                            payload["description"] = ni["comment"]
                        nb.ipam.ip_addresses.create(**payload)
                        lines[-1] += " ✓"
                    except Exception as ex:
                        lines[-1] += f" ✗ ({ex})"
        else:
            lines.append("  Tidak ada.")

        # Conflicts
        lines.append(f"\n[KONFLIK PREFIX] {len(ip_conflicts)} IP perlu verifikasi manual:")
        if ip_conflicts:
            for c in ip_conflicts:
                lines.append(
                    f"  Router: {c['router_addr']}  NetBox: {c['netbox_addr']}  "
                    f"interface={c['interface']}"
                )
            lines.append("  → Tidak diubah otomatis. Periksa dan update manual di NetBox.")
        else:
            lines.append("  Tidak ada.")

        # Summary
        lines.append(f"\n{'═' * 70}")
        if dry_run:
            lines.append(
                f"DRY-RUN selesai. Untuk eksekusi, jalankan ulang dengan dry_run=False."
            )
        else:
            lines.append(
                f"Selesai: {len(fixes)} fix parent, {len(new_ifaces)} interface baru, "
                f"{len(new_ips)} IP baru. {len(ip_conflicts)} konflik perlu manual."
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Gagal populate NetBox dari router: {e}"


# ── BGP plugin helpers ────────────────────────────────────────────────────────

def _bgp_auth_headers(cfg: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Token {cfg['token']}"}


def _bgp_api(nb, cfg: dict[str, Any], endpoint: str, **params) -> list[dict]:
    """GET all from NetBox BGP plugin endpoint."""
    url = f"{cfg['url'].rstrip('/')}/api/plugins/bgp/{endpoint}/"
    params.setdefault("limit", 1000)
    r = nb.http_session.get(url, params=params, headers=_bgp_auth_headers(cfg))
    r.raise_for_status()
    return r.json().get("results", [])


def _bgp_create(nb, cfg: dict[str, Any], endpoint: str, payload: dict) -> dict:
    url = f"{cfg['url'].rstrip('/')}/api/plugins/bgp/{endpoint}/"
    r = nb.http_session.post(url, json=payload, headers=_bgp_auth_headers(cfg))
    r.raise_for_status()
    return r.json()


def _bgp_patch(nb, cfg: dict[str, Any], endpoint: str, obj_id: int, payload: dict) -> dict:
    url = f"{cfg['url'].rstrip('/')}/api/plugins/bgp/{endpoint}/{obj_id}/"
    r = nb.http_session.patch(url, json=payload, headers=_bgp_auth_headers(cfg))
    r.raise_for_status()
    return r.json()


def _get_bgp_sessions_raw(entry: dict, creds: dict) -> tuple[bool, str, str]:
    ros = entry["ros_version"]
    cmd = "/routing/bgp/session/print" if ros == 7 else "routing bgp peer print"
    return ssh_run_command(
        host=entry["host"], username=creds["username"], password=creds["password"],
        command=cmd, port=creds["port"], timeout=creds["timeout"],
    )


def _get_bgp_filter_map(entry: dict, creds: dict) -> dict[str, dict[str, list[str]]]:
    """Return {conn_name: {input: [policy_names], output: [policy_names]}}."""
    ros = entry["ros_version"]
    cmd = "/routing/bgp/connection/print detail" if ros == 7 else "routing bgp peer print detail"
    ok, out, _ = ssh_run_command(
        host=entry["host"], username=creds["username"], password=creds["password"],
        command=cmd, port=creds["port"], timeout=creds["timeout"],
    )
    if not ok:
        return {}

    result: dict[str, dict[str, list[str]]] = {}
    current: str | None = None

    for raw_line in out.splitlines():
        s = raw_line.strip()
        if ros == 7:
            m_name = re.search(r'name="([^"]+)"', s)
        else:
            m_name = re.match(r'name=(\S+)', s)
        if m_name:
            current = m_name.group(1)
            result.setdefault(current, {"input": [], "output": []})
            continue
        if not current:
            continue
        if ros == 7:
            for m in re.finditer(r'input\.filter-chain=(\S+)', s):
                result[current]["input"].append(m.group(1))
            for m in re.finditer(r'output\.filter-chain=(\S+)', s):
                result[current]["output"].append(m.group(1))
        else:
            m_in = re.search(r'in-filter=(\S+)', s)
            m_out = re.search(r'out-filter=(\S+)', s)
            if m_in:
                result[current]["input"].append(m_in.group(1))
            if m_out:
                result[current]["output"].append(m_out.group(1))

    return result


@tool
def populate_netbox_bgp(
    router_name: str = "",
    instance: str = "idren",
) -> str:
    """
    Populate NetBox BGP plugin dengan data session dan routing-policy dari router MikroTik.
    Upsert: update jika session sudah ada (key: nama session), insert jika belum.
    Secara default memproses semua router role gate_idren. Routing-policy diambil
    dari filter chain di konfigurasi BGP connection/peer router.
    Args:
        router_name: Nama router spesifik. Kosong = semua router role gate_idren.
        instance: Instance NetBox — 'idren' (default), 'kampus', atau 'auto'.
    """
    from tools.routing import _parse_bgp_sessions

    try:
        if router_name.strip():
            rn = validate_router(router_name)
            entries = [get_router_entries(rn)[0]]
        else:
            entries = [e for e in get_unique_router_entries() if e.get("role") == "gate_idren"]

        if not entries:
            return "Tidak ada router gate_idren di config.yaml."

        cfg = _get_netbox_cfg(instance)
        nb = _nb(instance)
        all_lines: list[str] = []

        for entry in entries:
            creds = ssh_creds_for(entry)
            r_name = entry["name"]
            lines: list[str] = [f"\n── {r_name} ({entry['host']}) ──"]

            device = nb.dcim.devices.get(name=r_name)
            if not device:
                lines.append(f"  ✗ Device '{r_name}' tidak ada di NetBox DCIM — skip.")
                all_lines.extend(lines)
                continue

            ok, out, err = _get_bgp_sessions_raw(entry, creds)
            if not ok:
                lines.append(f"  ✗ SSH gagal: {err}")
                all_lines.extend(lines)
                continue

            sessions = _parse_bgp_sessions(out)
            if not sessions:
                lines.append("  Tidak ada BGP session.")
                all_lines.extend(lines)
                continue

            filter_map = _get_bgp_filter_map(entry, creds)

            def _match_filters(sname: str) -> dict[str, list[str]]:
                for conn, f in filter_map.items():
                    if sname == conn or sname.startswith(conn):
                        return f
                return {"input": [], "output": []}

            # Get default RIR for auto-created ASNs (use first available)
            _rirs = list(nb.ipam.rirs.all())
            _default_rir_id: int | None = _rirs[0].id if _rirs else None

            def _get_or_create_ip(ip: str, desc: str = "") -> int | None:
                if not ip:
                    return None
                for q in [ip, ip.split("/")[0] + "/32"]:
                    res = list(nb.ipam.ip_addresses.filter(address=q))
                    if res:
                        return res[0].id
                # Auto-create as /32
                addr = ip.split("/")[0] + "/32"
                payload: dict[str, Any] = {"address": addr, "status": "active"}
                if desc:
                    payload["description"] = desc
                obj = nb.ipam.ip_addresses.create(**payload)
                lines.append(f"    [auto-create IP] {addr}")
                return obj.id

            def _get_or_create_asn(asn_str: str) -> int | None:
                if not asn_str:
                    return None
                try:
                    asn_num = int(asn_str)
                    res = list(nb.ipam.asns.filter(asn=asn_num))
                    if res:
                        return res[0].id
                    p: dict[str, Any] = {"asn": asn_num}
                    if _default_rir_id:
                        p["rir"] = _default_rir_id
                    obj = nb.ipam.asns.create(**p)
                    lines.append(f"    [auto-create ASN] AS{asn_num}")
                    return obj.id
                except Exception:
                    return None

            created = updated = skipped = 0

            for s in sessions:
                remote_addr = s.get("remote_addr", "").split("%")[0]
                local_addr  = s.get("local_addr", "").split("%")[0]
                remote_as_str = s.get("remote_as", "")
                local_as_str  = s.get("local_as", "")

                # local_addr fallback: use device primary IP when parser couldn't capture it
                if not local_addr and device.primary_ip:
                    local_ip_id: int | None = device.primary_ip.id
                else:
                    local_ip_id = _get_or_create_ip(local_addr, f"BGP local — {r_name}")

                remote_ip_id = _get_or_create_ip(remote_addr, f"BGP peer — {s['name']}")
                local_as_id  = _get_or_create_asn(local_as_str)
                remote_as_id = _get_or_create_asn(remote_as_str)

                if not local_ip_id or not remote_ip_id or not local_as_id or not remote_as_id:
                    missing: list[str] = []
                    if not local_ip_id:
                        missing.append(f"local_ip (tidak ada primary_ip di NetBox)")
                    if not remote_ip_id:
                        missing.append(f"remote_addr={remote_addr or '?'}")
                    if not local_as_id:
                        missing.append(f"local_as={local_as_str or '?'}")
                    if not remote_as_id:
                        missing.append(f"remote_as={remote_as_str or '?'}")
                    lines.append(f"  ✗ {s['name']}: unresolvable — {'; '.join(missing)}")
                    skipped += 1
                    continue

                filters = _match_filters(s["name"])
                import_ids: list[int] = []
                export_ids: list[int] = []

                for pname in filters.get("input", []):
                    existing = _bgp_api(nb, cfg, "routing-policy", name=pname)
                    if existing:
                        import_ids.append(existing[0]["id"])
                    else:
                        obj = _bgp_create(nb, cfg, "routing-policy", {
                            "name": pname, "description": f"Input filter — {r_name}"
                        })
                        import_ids.append(obj["id"])

                for pname in filters.get("output", []):
                    existing = _bgp_api(nb, cfg, "routing-policy", name=pname)
                    if existing:
                        export_ids.append(existing[0]["id"])
                    else:
                        obj = _bgp_create(nb, cfg, "routing-policy", {
                            "name": pname, "description": f"Output filter — {r_name}"
                        })
                        export_ids.append(obj["id"])

                payload: dict[str, Any] = {
                    "name": s["name"],
                    "device": device.id,
                    "local_address": local_ip_id,
                    "remote_address": remote_ip_id,
                    "local_as": local_as_id,
                    "remote_as": remote_as_id,
                    "status": "active" if s.get("established") else "offline",
                }
                if import_ids:
                    payload["import_policies"] = import_ids
                if export_ids:
                    payload["export_policies"] = export_ids

                try:
                    existing_sessions = _bgp_api(nb, cfg, "session", name=s["name"])
                    if existing_sessions:
                        _bgp_patch(nb, cfg, "session", existing_sessions[0]["id"], payload)
                        action = "updated"
                        updated += 1
                    else:
                        _bgp_create(nb, cfg, "session", payload)
                        action = "created"
                        created += 1
                    icon = "✓" if s["established"] else "✗"
                    lines.append(f"  [{action}] {icon} {s['name']}  AS{remote_as_str}")
                except Exception as ex:
                    lines.append(f"  ✗ {s['name']}: {ex}")
                    skipped += 1

            lines.append(f"\n  Ringkasan: {created} dibuat, {updated} diupdate, {skipped} dilewati")
            all_lines.extend(lines)

        return "\n".join(all_lines) or "Tidak ada data untuk diproses."

    except Exception as e:
        return f"Gagal populate NetBox BGP: {e}"


@tool
def resolve_router_host(router_name: str) -> str:
    """
    Auto-discover dan set host IP untuk router yang host-nya kosong di config.yaml.
    Strategi berurutan:
    1. NetBox primary_ip — lookup device by name di NetBox instance yang sesuai
    2. NetBox BGP sessions — ambil local_address dari session BGP milik device ini
    3. BGP peer discovery — SSH ke router lain yang sudah punya host, cari remote_addr
       dari session yang mengarah ke router target
    Jika IP ditemukan: update primary_ip di NetBox + update cache in-memory.
    Config.yaml tidak diubah — NetBox adalah source of truth.
    Args:
        router_name: Nama router di config.yaml yang host-nya kosong atau perlu diverifikasi.
    """
    from tools.routing import _parse_bgp_sessions
    from tools.base import (
        validate_router, get_router_entries, get_unique_router_entries,
        ssh_creds_for,
    )

    try:
        router_name = validate_router(router_name)
        entries = get_router_entries(router_name)
        if not entries:
            return f"Router '{router_name}' tidak ditemukan di config.yaml."

        entry = entries[0]
        current_host = entry.get("host", "").strip()
        if current_host:
            return (
                f"Router '{router_name}' sudah punya host={current_host}.\n"
                f"Tidak perlu resolusi. Gunakan tool SSH langsung."
            )

        network = entry.get("network", "kampus")
        cfg = _get_netbox_cfg(network)
        nb = _nb(network)

        discovered_ip: str | None = None
        method: str = ""

        # === Strategi 1: NetBox primary_ip ===
        device = nb.dcim.devices.get(name=router_name)
        if device and device.primary_ip:
            discovered_ip = str(device.primary_ip.address).split("/")[0]
            method = "NetBox primary_ip"

        # === Strategi 2: NetBox BGP sessions — local_address ===
        if not discovered_ip and device:
            bgp_sessions = _bgp_api(nb, cfg, "session", device_id=device.id)
            for s in bgp_sessions:
                la = s.get("local_address", {})
                addr = la.get("address", "") if isinstance(la, dict) else str(la)
                if addr:
                    discovered_ip = addr.split("/")[0]
                    method = f"NetBox BGP session local_address (session={s.get('name', '?')})"
                    break

        # === Strategi 3: BGP peer discovery via router lain ===
        if not discovered_ip:
            candidates = [
                e for e in get_unique_router_entries()
                if e.get("network") == network
                and e.get("host", "").strip()
                and e["name"] != router_name
            ]
            for c in candidates:
                c_creds = ssh_creds_for(c)
                cmd = "/routing/bgp/session/print" if c["ros_version"] == 7 else "routing bgp peer print"
                ok, out, _ = ssh_run_command(
                    host=c["host"], username=c_creds["username"], password=c_creds["password"],
                    command=cmd, port=c_creds["port"], timeout=c_creds["timeout"],
                )
                if not ok:
                    continue
                for s in _parse_bgp_sessions(out):
                    if router_name.lower() in s.get("name", "").lower():
                        remote_addr = s.get("remote_addr", "").split("%")[0]
                        if remote_addr:
                            discovered_ip = remote_addr
                            method = f"BGP peer discovery via {c['name']} (session={s['name']})"
                            break
                if discovered_ip:
                    break

        if not discovered_ip:
            return (
                f"Tidak bisa auto-discover host IP untuk router '{router_name}'.\n"
                f"Strategi dicoba: NetBox primary_ip → NetBox BGP sessions → BGP peer discovery.\n"
                f"Tambahkan host IP manual di config.yaml atau set primary_ip di NetBox."
            )

        # === Update NetBox primary_ip ===
        nb_update_msg = "(NetBox: device tidak ditemukan — primary_ip tidak diupdate)"
        if device:
            ip_objs = list(nb.ipam.ip_addresses.filter(address=f"{discovered_ip}/32"))
            if not ip_objs:
                ip_objs = list(nb.ipam.ip_addresses.filter(address=discovered_ip))
            if ip_objs:
                try:
                    device.update({"primary_ip4": ip_objs[0].id})
                    nb_update_msg = (
                        f"NetBox primary_ip diupdate → {discovered_ip}\n"
                        f"  NetBox    : {_nb_url(cfg['url'], 'device', device.id)}"
                    )
                except Exception as ex:
                    nb_update_msg = f"NetBox primary_ip update gagal: {ex}"
            else:
                nb_update_msg = (
                    f"NetBox: IP {discovered_ip} belum ada di IPAM — primary_ip tidak diupdate.\n"
                    f"Jalankan add_netbox_ip_address() untuk tambah IP dulu."
                )

        # === Update config.yaml + reload in-memory ===
        from tools.config_yaml import patch_router_host as _patch_host
        cfg_result = _patch_host.invoke({"router_name": router_name, "host": discovered_ip})

        return (
            f"Host IP berhasil di-resolve untuk router '{router_name}'.\n"
            f"  IP     : {discovered_ip}\n"
            f"  Metode : {method}\n"
            f"  {nb_update_msg}\n"
            f"  {cfg_result}"
        )

    except Exception as e:
        return f"Gagal resolve host untuk '{router_name}': {e}"


@tool
def get_netbox_bgp_drift(
    router_name: str = "",
    instance: str = "idren",
) -> str:
    """
    Bandingkan BGP sessions di NetBox (expected) vs live di router (actual).
    Laporan: session hanya di NetBox, hanya di router, atau status mismatch.
    Gunakan setelah populate_netbox_bgp() untuk verifikasi sinkronisasi.
    Args:
        router_name: Nama router spesifik. Kosong = semua router role gate_idren.
        instance: Instance NetBox — 'idren' (default), 'kampus', atau 'auto'.
    """
    from tools.routing import _parse_bgp_sessions

    try:
        if router_name.strip():
            rn = validate_router(router_name)
            entries = [get_router_entries(rn)[0]]
        else:
            entries = [e for e in get_unique_router_entries() if e.get("role") == "gate_idren"]

        if not entries:
            return "Tidak ada router gate_idren di config.yaml."

        cfg = _get_netbox_cfg(instance)
        nb = _nb(instance)

        lines = [f"BGP Drift — NetBox vs Router  [{instance.upper()}]", "═" * 70]
        any_drift = False

        for entry in entries:
            creds = ssh_creds_for(entry)
            r_name = entry["name"]
            lines.append(f"\n── {r_name} ({entry['host']}) ──")

            device = nb.dcim.devices.get(name=r_name)
            if not device:
                lines.append(f"  ✗ Device '{r_name}' tidak ada di NetBox — skip.")
                continue

            nb_raw = _bgp_api(nb, cfg, "session", device_id=device.id)
            nb_sessions = {s["name"]: s for s in nb_raw}

            ok, out, err = _get_bgp_sessions_raw(entry, creds)
            if not ok:
                lines.append(f"  ✗ SSH gagal: {err}")
                continue
            live_sessions = {s["name"]: s for s in _parse_bgp_sessions(out)}

            only_nb     = set(nb_sessions) - set(live_sessions)
            only_router = set(live_sessions) - set(nb_sessions)
            common      = set(nb_sessions) & set(live_sessions)

            if only_nb:
                any_drift = True
                lines.append(f"  ⚠ Di NetBox, tidak di router ({len(only_nb)}):")
                for n in sorted(only_nb):
                    lines.append(f"    - {n}")

            if only_router:
                any_drift = True
                lines.append(f"  ⚠ Di router, tidak di NetBox ({len(only_router)}):")
                for n in sorted(only_router):
                    ls = live_sessions[n]
                    icon = "✓" if ls["established"] else "✗"
                    lines.append(f"    - {n}  AS{ls.get('remote_as', '?')}  {icon}")

            mismatches: list[tuple[str, str, str]] = []
            for n in common:
                nb_st_raw = nb_sessions[n].get("status", {})
                nb_st = nb_st_raw.get("value", "") if isinstance(nb_st_raw, dict) else str(nb_st_raw)
                live_st = "active" if live_sessions[n]["established"] else "offline"
                if nb_st != live_st:
                    mismatches.append((n, nb_st, live_st))

            if mismatches:
                any_drift = True
                lines.append(f"  ⚠ Status mismatch ({len(mismatches)}):")
                for n, nb_st, live_st in mismatches:
                    lines.append(f"    - {n}: NetBox={nb_st} ↔ Router={live_st}")

            if not only_nb and not only_router and not mismatches:
                lines.append(f"  ✓ Sinkron — {len(nb_sessions)} session cocok.")

        lines.append("\n" + "═" * 70)
        lines.append(
            "Ada drift. Jalankan populate_netbox_bgp() untuk sinkronisasi."
            if any_drift else "✓ Semua router sinkron."
        )
        return "\n".join(lines)

    except Exception as e:
        return f"Gagal get BGP drift: {e}"
