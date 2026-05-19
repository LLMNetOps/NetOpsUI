---
name: netbox-bgp-sync
domain: config
triggers:
  - drift bgp netbox
  - sinkronisasi bgp netbox
  - bgp netbox tidak sinkron
  - populate bgp ke netbox
  - bgp session belum ada di netbox
  - sync bgp session ke netbox
  - bgp di router tidak di netbox
  - rekonsiliasi bgp netbox
  - update bgp netbox dari router
  - cek drift bgp
tools:
  - get_netbox_bgp_drift
  - populate_netbox_bgp
approval_required: true
enabled: true
---

# Prosedur Sinkronisasi BGP NetBox

## Konteks

Skill ini untuk mendeteksi dan memperbaiki drift antara data BGP session di NetBox
(dokumentasi expected state) vs BGP session live di router MikroTik.

**Arah sinkronisasi: Router → NetBox.**
Router adalah sumber kebenaran BGP aktual. NetBox adalah dokumentasi — diisi
dari kondisi nyata router, bukan sebaliknya.

Ini berbeda dengan VLAN sync (NetBox → Router). Jangan campur alurnya.

## Parameter `instance`

Semua tools di skill ini default ke `instance="idren"` — BGP session di jaringan
IDREN. Override ke `instance="kampus"` hanya jika konteks memang kampus.

## Langkah Eksekusi

### Langkah 1: Jalankan BGP Drift Report

```
get_netbox_bgp_drift(router_name="<nama-router>")
```

Kosongkan `router_name` untuk cek semua router `gate_idren` sekaligus.

Output terbagi tiga kategori per router:
- **Di NetBox, tidak di router** — session terdokumentasi tapi tidak aktif di router
- **Di router, tidak di NetBox** — session live tapi belum terdokumentasi di NetBox
- **Status mismatch** — session ada di keduanya tapi status berbeda (NetBox: active, router: offline atau sebaliknya)

Jika drift report menunjukkan "Semua router sinkron" → laporkan ke operator, selesai.

### Langkah 2: Analisis Jenis Drift

Bedakan tiga situasi — penanganannya berbeda:

| Jenis Drift | Artinya | Aksi |
|-------------|---------|------|
| Di router, tidak di NetBox | Session baru di router, belum terdokumentasi | `populate_netbox_bgp` (Langkah 3) |
| Di NetBox, tidak di router | Session dihapus dari router tapi masih di NetBox | Laporkan ke operator — jangan hapus otomatis |
| Status mismatch | Session ada di keduanya, status berbeda | Laporkan ke operator — cek apakah session memang down |

### Langkah 3: Populate NetBox dari Router (jika ada session baru)

Presentasikan rencana ke operator sebelum eksekusi:

```
Rencana populate BGP ke NetBox:

Router   : <nama-router>
Instance : IDREN

Session yang akan ditambahkan ke NetBox:
  - <nama-session>  AS<remote-as>  <remote-address>
  - ...

Tool akan upsert session (update jika sudah ada, insert jika belum).
IP dan ASN baru akan dibuat otomatis di NetBox jika belum ada.

Approval diperlukan sebelum eksekusi.
```

Setelah operator setuju, jalankan:

```
populate_netbox_bgp(router_name="<nama-router>", instance="idren")
```

Sistem akan meminta approval operator via interrupt gate.

### Langkah 4: Verifikasi Pasca Populate

Jalankan drift report ulang untuk konfirmasi:

```
get_netbox_bgp_drift(router_name="<nama-router>")
```

Pastikan kategori "Di router, tidak di NetBox" sudah kosong.
Jika masih ada sisa → investigasi dan laporkan ke operator.

## Kasus Khusus

### Session di NetBox tapi Tidak di Router

Jangan hapus otomatis — ini bisa berarti:
- Session memang dihapus dari router (perlu cleanup di NetBox)
- Session sementara down (jangan hapus)

Laporkan ke operator dengan detail:
```
Perhatian: <N> session ada di NetBox tapi tidak ditemukan di router <nama>:
  - <nama-session> (status NetBox: active)

Apakah session ini sudah dihapus dari router? Jika ya, hapus manual di NetBox UI.
```

### Status Mismatch (NetBox: active, Router: offline)

Bisa berarti session BGP memang sedang down — bukan masalah sinkronisasi.
Laporkan ke operator, arahkan ke monitor_agent jika perlu investigasi BGP.

### Device Tidak Ada di NetBox DCIM

Tool akan skip router tersebut dan melaporkan error.
Jika router memang perlu ditambahkan ke NetBox, gunakan NetBox UI untuk tambahkan
device baru di DCIM terlebih dahulu.

## Validasi Mandiri

Sebelum lapor ke operator, pastikan:
- [ ] Drift report sudah dijalankan sebelum populate
- [ ] Bedakan kategori drift (router→NB vs NB→router vs mismatch) sebelum eksekusi
- [ ] Verifikasi drift report ulang setelah populate

## Handoff

| Kondisi | Aksi | Agent Tujuan |
|---------|------|--------------|
| Session BGP down (bukan drift) | Serahkan investigasi BGP | monitor_agent |
| Sinkronisasi selesai — perlu laporan | Serahkan ringkasan perubahan | document_agent |
| Tidak ada drift | Tidak perlu handoff | END |
