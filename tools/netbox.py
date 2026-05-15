"""Tool: NetBox IPAM integration — query devices, interfaces, IPs, drift detection."""

from __future__ import annotations

import re
from typing import Any

import yaml
from langchain_core.tools import tool

from tools.base import CONFIG_FILE, validate_router, get_router_entries, ssh_creds, ssh_run_command


# ── NetBox client ─────────────────────────────────────────────────────────────

def _get_netbox_cfg() -> dict[str, Any]:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        nb = cfg.get("netbox", {})
        if not nb.get("url") or not nb.get("token"):
            raise ValueError(
                "config.yaml harus memiliki:\n"
                "netbox:\n  url: https://ipam.example.com\n  token: <api-token>"
            )
        return nb
    except FileNotFoundError:
        raise ValueError("config.yaml tidak ditemukan")


def _nb():
    """Return authenticated pynetbox API client."""
    try:
        import pynetbox
    except ImportError:
        raise ImportError("pynetbox belum terinstall. Jalankan: pip install pynetbox>=7.0")
    cfg = _get_netbox_cfg()
    nb = pynetbox.api(cfg["url"], token=cfg["token"])
    if not cfg.get("ssl_verify", True):
        import requests
        s = requests.Session()
        s.verify = False
        nb.http_session = s
    return nb


# ── Helpers ───────────────────────────────────────────────────────────────────

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
def get_netbox_devices() -> str:
    """
    Ambil daftar semua device jaringan di NetBox beserta primary IP dan status.
    Berguna untuk melihat inventaris dan mencari nama device yang sesuai dengan router.
    """
    try:
        nb = _nb()
        devices = list(nb.dcim.devices.all())
        if not devices:
            return "Tidak ada device ditemukan di NetBox."

        lines = [f"Device di NetBox ({len(devices)} total)", "─" * 60]
        for d in sorted(devices, key=lambda x: x.name):
            primary_ip = str(d.primary_ip.address) if d.primary_ip else "—"
            status = str(d.status)
            site = str(d.site) if d.site else "—"
            lines.append(
                f"  {d.name:<35} primary_ip={primary_ip:<22} status={status}  site={site}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Gagal mengambil devices dari NetBox: {e}"


@tool
def get_netbox_device_interfaces(device_name: str) -> str:
    """
    Ambil daftar virtual interface device di NetBox.
    Prioritaskan interface bertag 'managed-by-agent'; jika belum ada tag, tampilkan semua virtual.
    Loopback dan interface fisik dilewati.
    Args:
        device_name: Nama device di NetBox. Gunakan get_netbox_devices() untuk daftar valid.
    """
    try:
        nb = _nb()
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
def get_netbox_device_ips(device_name: str) -> str:
    """
    Ambil semua IP address yang di-assign ke device di NetBox.
    Args:
        device_name: Nama device di NetBox. Gunakan get_netbox_devices() untuk daftar valid.
    """
    try:
        nb = _nb()
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
def get_netbox_drift_report(router_name: str, device_name: str = "") -> str:
    """
    Bandingkan konfigurasi interface VLAN dan IP di NetBox vs kondisi aktual router MikroTik.
    Matching interface: berdasarkan VLAN ID (bukan nama — nama bisa berbeda antara NetBox dan router).
    Matching device: cari device NetBox yang punya IP = host router di config.yaml.
    Args:
        router_name: Nama router di config.yaml. Gunakan list_routers() untuk daftar valid.
        device_name: (opsional) Nama device di NetBox jika auto-matching gagal.
    """
    try:
        router_name = validate_router(router_name)
        entry = get_router_entries(router_name)[0]
        creds = ssh_creds()
        router_host = entry["host"]
        ros = entry["ros_version"]

        nb = _nb()

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


# ── Write tools (approval required via netbox_agent definition) ───────────────

@tool
def add_netbox_ip_address(
    ip_with_prefix: str,
    interface_name: str,
    device_name: str,
    description: str = "",
) -> str:
    """
    Tambahkan IP address ke interface device di NetBox. MEMERLUKAN APPROVAL OPERATOR.
    Gunakan saat IP baru perlu didokumentasikan di NetBox sebagai source of truth.
    Args:
        ip_with_prefix: IP dengan prefix notation (contoh: 192.168.10.1/24)
        interface_name: Nama interface di NetBox. Gunakan get_netbox_device_interfaces().
        device_name: Nama device di NetBox. Gunakan get_netbox_devices().
        description: Deskripsi IP (opsional)
    """
    try:
        nb = _nb()
        interfaces = list(nb.dcim.interfaces.filter(device=device_name, name=interface_name))
        if not interfaces:
            return f"Interface '{interface_name}' tidak ditemukan untuk device '{device_name}' di NetBox."
        iface = interfaces[0]

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
            f"  ID       : {result.id}\n"
            f"  Address  : {result.address}\n"
            f"  Device   : {device_name}\n"
            f"  Interface: {interface_name}"
        )
    except Exception as e:
        return f"Gagal menambahkan IP address ke NetBox: {e}"


@tool
def update_netbox_interface(
    interface_name: str,
    device_name: str,
    description: str | None = None,
    enabled: bool | None = None,
) -> str:
    """
    Update properties interface di NetBox. MEMERLUKAN APPROVAL OPERATOR.
    Minimal satu dari description atau enabled harus diisi.
    Args:
        interface_name: Nama interface di NetBox
        device_name: Nama device di NetBox. Gunakan get_netbox_devices().
        description: Deskripsi baru interface (opsional)
        enabled: Status interface — True=enabled, False=disabled (opsional)
    """
    try:
        nb = _nb()
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
            f"  Perubahan : {changed}"
        )
    except Exception as e:
        return f"Gagal update interface di NetBox: {e}"


@tool
def populate_netbox_from_router(
    router_name: str,
    device_name: str = "",
    dry_run: bool = True,
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
    """
    try:
        router_name = validate_router(router_name)
        entry = get_router_entries(router_name)[0]
        creds = ssh_creds()
        router_host = entry["host"]
        ros = entry["ros_version"]

        nb = _nb()

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
