---
name: vlan-provisioning
domain: config
triggers:
  - tambah vlan baru
  - buat vlan baru
  - provisioning vlan
  - tambah koneksi baru
  - tambah link baru
  - buat interface vlan
  - tambah interface vlan
  - link baru via isp
  - link redundan
  - vlan baru untuk idren
tools:
  - get_netbox_vlan_groups
  - get_next_available_vlan
  - create_netbox_vlan_interface
  - add_netbox_ip_address
  - get_netbox_devices
  - get_netbox_device_interfaces
  - check_reachability
  - run_command
approval_required: true
enabled: true
---

# Provisioning VLAN Baru — NetBox sebagai Source of Truth

## Konteks

Gunakan skill ini untuk menambahkan VLAN interface baru di jaringan IDREN.
Alur: **NetBox dulu, router kemudian** — NetBox adalah source of truth.

Arah: Buat di NetBox → handoff ke config_agent untuk eksekusi di router.

## Validasi Input

Sebelum mulai, pastikan operator sudah berikan info lengkap.
Jika belum, **tanya balik** dengan format ini:

```
Untuk membuat VLAN baru, saya butuh informasi berikut:

Tipe: link-idren | uplink | server | peering-langsung

Lengkapi sesuai tipe:
- link-idren    → tujuan: [nama node di NetBox] + ISP: [CBN/BIZNET/TELKOM/STARLINK/dll]
- uplink        → ISP: [nama ISP]
- server        → fungsi: [PUBLIC/MGMT/CCTV/dst]
- peering       → tujuan: [nama device] + medium: FIBER

Contoh input yang valid:
- "vlan baru link-idren ke NODE-IDREN-ITB via BIZNET"
- "tambah uplink via STARLINK"
- "buat vlan server CCTV"
- "vlan peering ke GATE-ARENAPAC via FIBER"
```

## Langkah Provisioning

### Langkah 1: Tentukan VLAN Group dan ID

Dari input operator, tentukan ISP/tipe → VLAN group:

```
get_netbox_vlan_groups()
```

Mapping tipe ke group (gunakan nama group yang mengandung nama ISP):
- CBN → `vg-cbn` (701–750)
- TELKOM → `vg-telkom` (2001–2050) atau `vg-telkom-2` (501–550)
- BIZNET → cari group yang sesuai, atau laporkan ke operator jika tidak ada
- STARLINK → cari group, atau gunakan `vg-gate-idren` jika link IDREN
- MGMT → `vg-mgmt` (2–100)

```
get_next_available_vlan(group_slug="<slug>")
```

Tampilkan VLAN ID yang akan digunakan ke operator sebelum lanjut.

### Langkah 2: Tentukan Format Description

Dari input operator, construct description sesuai standar:

| Tipe | Format | Contoh |
|------|--------|--------|
| link-idren | `TO GATE-IDREN-<DEST> VIA <ISP>` | `TO GATE-IDREN-ITB VIA BIZNET` |
| uplink | `UPLINK VIA <ISP>` | `UPLINK VIA STARLINK` |
| server | `SRV <fungsi>` | `SRV CCTV` |
| peering | `TO <DEST> VIA FIBER` | `TO GATE-ARENAPAC VIA FIBER` |

### Langkah 3: Tentukan Parent Interface

Tanyakan ke operator atau cek dari konteks:
```
get_netbox_device_interfaces(device_name="GATE-IDREN-UB")
```

Parent interface biasanya interface fisik (ether, sfp, bond) yang menjadi trunk.
Jika operator tidak tahu, tampilkan daftar interface fisik yang ada.

### Langkah 4: Konfirmasi ke Operator

Sebelum eksekusi, tampilkan rencana lengkap:

```
Rencana provisioning VLAN baru:

Device      : GATE-IDREN-UB
Interface   : vlan<ID>
VLAN ID     : <ID>  (dari group <nama-group>, range <min>-<max>)
Parent      : <parent-interface>
Description : <description>

Langkah yang akan dieksekusi:
1. [NetBox] Buat interface vlan<ID> di NetBox (approval diperlukan)
2. [NetBox] Assign IP address <ip/prefix> ke interface (approval diperlukan)
3. [Router] Handoff ke config_agent untuk buat interface di GATE-IDREN-UB

Lanjutkan?
```

### Langkah 5: Buat Interface di NetBox

```
create_netbox_vlan_interface(
    device_name="GATE-IDREN-UB",
    vlan_id=<ID>,
    parent_interface="<parent>",
    description="<description>"
)
```

Sistem akan meminta approval operator sebelum eksekusi.

### Langkah 6: Assign IP di NetBox (jika sudah diketahui)

Jika operator sudah tahu IP yang akan digunakan:

```
add_netbox_ip_address(
    ip_with_prefix="<ip/prefix>",
    interface_name="vlan<ID>",
    device_name="GATE-IDREN-UB",
    description="<description>"
)
```

Jika IP belum ditentukan: catat bahwa IP perlu ditambahkan nanti setelah
koordinasi dengan peer/ISP.

### Langkah 7: Handoff ke config_agent

Setelah NetBox diupdate, handoff ke config_agent (joko) dengan instruksi:

```
Tolong konfigurasi router GATE-IDREN-UB:

1. Buat VLAN interface:
   /interface/vlan/add name="vlan<ID>" vlan-id=<ID> interface=<parent> comment="<description>"

2. Assign IP address (jika sudah ada):
   /ip/address/add address=<ip/prefix> interface="vlan<ID>" comment="<description>"

Backup config sebelum memulai. Verifikasi setelah eksekusi.
```

### Langkah 8: Verifikasi

Setelah config_agent selesai, verifikasi:
- Interface baru muncul di router: `run_command("GATE-IDREN-UB", "/interface/vlan/print")`
- IP ter-assign: `run_command("GATE-IDREN-UB", "/ip/address/print")`
- Drift report bersih: drift antara NetBox dan router seharusnya nol

## Kasus Khusus

### VLAN Group Penuh

Jika `get_next_available_vlan` mengembalikan "sudah penuh":
1. Laporkan ke operator beserta group yang penuh dan range-nya
2. Tanyakan apakah perlu extend range group tersebut atau buat group baru
3. Operator update di NetBox UI (Settings → IPAM → VLAN Groups)
4. Setelah range diupdate, jalankan `get_next_available_vlan` ulang

Group yang sudah penuh per data saat ini: CBN, ICON+, SDI, LINKNET, ARENAPAC,
PGNCOM, XL AXIATA, HSP, iFORTE, IMS, Indosat, Lintasarta.
Group yang masih tersedia: Telkom (sisa 24), GATE-IDREN (sisa 51), GATE-IDREN-01 (sisa 2277).

### VLAN Group Belum Ada untuk ISP Baru

Jika ISP tidak punya group di NetBox:
1. Laporkan ke operator: "Group untuk ISP [nama] belum ada di NetBox"
2. Minta operator buat VLAN group baru di NetBox UI (Settings → IPAM → VLAN Groups)
3. Setelah group dibuat, lanjutkan provisioning

### IP Belum Diketahui Saat Provisioning

Normal terjadi saat koneksi baru sedang dinegosiasikan dengan ISP.
Buat interface di NetBox dan router tanpa IP dulu.
IP ditambahkan via `add_netbox_ip_address` setelah koordinasi dengan ISP/peer selesai.

## Catatan

- **NetBox selalu dulu** — jangan buat di router sebelum NetBox diupdate
- Nama interface di router WAJIB `vlan<ID>` — bukan nama panjang dari NetBox lama
- Approval diperlukan untuk setiap write ke NetBox dan ke router
- Setelah VLAN aktif: update VLAN group di NetBox (tandai ID sebagai "Active")
