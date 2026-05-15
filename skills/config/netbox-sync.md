---
name: netbox-sync
domain: config
triggers:
  - sinkronisasi netbox
  - sync netbox ke router
  - terapkan konfigurasi dari netbox
  - konfigurasi interface dari netbox
  - push netbox ke mikrotik
  - rekonsiliasi netbox
  - drift netbox
  - netbox ke router
  - update router dari netbox
tools:
  - get_netbox_drift_report
  - get_netbox_device_interfaces
  - get_netbox_device_ips
  - run_command
  - check_reachability
approval_required: true
enabled: true
---

# Prosedur Sinkronisasi NetBox → MikroTik

## Konteks

Gunakan skill ini untuk mendeteksi perbedaan (drift) antara data NetBox dan kondisi
aktual router MikroTik, kemudian mengeksekusi perubahan ke router agar sesuai dengan
NetBox sebagai source of truth.

**Arah sinkronisasi: NetBox → MikroTik (satu arah).**
NetBox adalah master — jangan ubah NetBox untuk menyesuaikan router.

## Langkah Eksekusi

### Langkah 1: Jalankan Drift Report

```
get_netbox_drift_report(router_name="<nama-router>")
```

Catat dengan teliti:
- Interface yang perlu DIBUAT di router (ada di NetBox, belum ada di router)
- IP yang perlu DITAMBAH di router (ada di NetBox, belum ada di router)
- Item informasional (ada di router, tidak di NetBox) — tidak diubah

Jika drift report menunjukkan "Tidak ada drift" → laporkan ke operator, selesai.

### Langkah 2: Presentasikan Rencana Perubahan

Sebelum handoff ke config_agent, jelaskan ke operator secara eksplisit:

```
Rencana sinkronisasi NetBox → Router <nama-router>:

INTERFACE yang akan dibuat:
  /interface/vlan/add name=<nama> vlan-id=<id> interface=<parent> comment="<desc>"

IP ADDRESS yang akan ditambah:
  /ip/address/add address=<ip/prefix> interface=<nama-interface> comment="<desc>"

Total perubahan: X interface + Y IP address
```

Tunggu konfirmasi operator sebelum lanjut ke handoff.

### Langkah 3: Handoff ke config_agent

Setelah operator konfirmasi, serahkan eksekusi ke config_agent (Joko) dengan
instruksi spesifik untuk setiap perubahan.

**Format instruksi handoff:**
```
Tolong konfigurasi router <nama-router> sesuai data NetBox berikut:

1. Buat VLAN interface:
   /interface/vlan/add name="<nama>" vlan-id=<id> interface=<parent> comment="<desc>"

2. Tambah IP address:
   /ip/address/add address=<ip/prefix> interface=<nama-interface> comment="<desc>"

Backup config sebelum memulai. Verifikasi setiap perubahan setelah eksekusi.
```

### Langkah 4: Verifikasi Pasca Sinkronisasi

Setelah config_agent selesai, jalankan drift report ulang untuk konfirmasi:

```
get_netbox_drift_report(router_name="<nama-router>")
```

Pastikan hasilnya "Tidak ada drift". Jika masih ada drift → investigasi penyebabnya.

## Perintah MikroTik yang Dihasilkan dari Data NetBox

### Membuat VLAN Interface

Data sumber dari `get_netbox_device_interfaces()`:
- `name` → nama interface (juga dipakai sebagai nama VLAN di MikroTik)
- `vlan_id` (custom field) → `vlan-id`
- `parent` → `interface` (parent fisik)
- `description` → `comment` (diawali `;;;` di MikroTik)

```
/interface/vlan/add \
  name="<nama-dari-netbox>" \
  vlan-id=<vlan_id-dari-custom-field> \
  interface=<parent-interface> \
  comment="<description>"
```

### Menambah IP Address

Data sumber dari `get_netbox_device_ips()`:
- `address` → `address` (sudah dalam format IP/prefix)
- `assigned_object` → `interface`
- `description` → `comment`

```
/ip/address/add \
  address=<ip/prefix> \
  interface=<nama-interface> \
  comment="<description>"
```

## Aturan Keamanan

- SELALU backup config sebelum perubahan: `backup_router_config(router_name)`
- JANGAN ubah interface yang tidak ada tag `managed-by-agent` di NetBox
- JANGAN hapus konfigurasi yang ada di router tapi tidak di NetBox — hanya tambah
- Jika ada konflik (VLAN ID sudah dipakai interface lain) → laporkan ke operator,
  jangan paksa eksekusi
- Verifikasi reachability router sebelum dan sesudah perubahan

## Catatan Penting

**Custom field `vlan_id` wajib ada** di NetBox untuk setiap interface virtual yang
perlu dibuat di MikroTik. Jika kosong, drift report akan menampilkan `vlan-id=?` dan
interface tersebut **tidak bisa dikonfigurasi** sampai data dilengkapi.

**Nama interface harus konsisten** antara NetBox dan MikroTik — gunakan nama yang sama
persis. Ini yang dipakai sebagai key untuk mendeteksi drift.
