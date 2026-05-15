---
name: netbox-read
domain: monitoring
triggers:
  - cek netbox
  - lihat data netbox
  - inventaris netbox
  - interface di netbox
  - ip address di netbox
  - device di netbox
  - audit netbox
  - verifikasi netbox
  - data source of truth
tools:
  - get_netbox_devices
  - get_netbox_device_interfaces
  - get_netbox_device_ips
approval_required: false
enabled: true
---

# Prosedur Query Inventaris NetBox

## Konteks

Gunakan skill ini untuk membaca dan memverifikasi data inventaris jaringan dari NetBox
(source of truth). Tidak ada perubahan yang dilakukan — hanya baca dan audit.

## Langkah Eksekusi

### 1. Tampilkan Daftar Device

```
get_netbox_devices()
```

Catat nama device dan primary_ip. Primary IP harus cocok dengan host di config.yaml
agar drift report bisa berjalan.

### 2. Query Interface Device Tertentu

```
get_netbox_device_interfaces(device_name="<nama-device>")
```

Hanya interface dengan tag `managed-by-agent` yang ditampilkan. Jika kosong:
- Ingatkan operator untuk menambahkan tag `managed-by-agent` di NetBox pada interface
  yang ingin di-manage oleh agent.

Data yang ditampilkan per interface:
- Nama, tipe, parent interface
- VLAN ID (dari custom field `vlan_id`)
- Status enabled/disabled
- IP address yang sudah di-assign

### 3. Query IP Addresses Device

```
get_netbox_device_ips(device_name="<nama-device>")
```

Menampilkan semua IP yang sudah terdokumentasi di NetBox untuk device tersebut,
termasuk interface yang di-assign dan status IP.

## Checklist Audit NetBox

Saat melakukan audit inventaris, verifikasi hal berikut:

| Item | Yang Dicek |
|------|------------|
| Primary IP | Setiap device punya primary_ip yang = IP loopback/MGMT di router |
| Tag managed-by-agent | Interface yang perlu di-sync sudah ditag |
| VLAN ID | Custom field `vlan_id` terisi untuk interface tipe virtual |
| Parent interface | Field parent terisi (interface fisik yang menjadi trunk) |
| IP assignment | Setiap IP sudah di-assign ke interface yang benar |

## Output yang Diharapkan

- Daftar device dengan primary IP dan status
- Daftar interface managed beserta VLAN ID, parent, dan IP
- Identifikasi data yang tidak lengkap di NetBox (vlan_id kosong, parent kosong, dll)
- Rekomendasi perbaikan data NetBox jika ditemukan ketidaklengkapan
