---
name: router-to-netbox-sync
domain: config
triggers:
  - sinkronisasi router ke netbox
  - populate netbox dari router
  - interface di router belum di netbox
  - ip di router belum terdokumentasi
  - onboarding router ke netbox
  - router lebih lengkap dari netbox
  - netbox tidak lengkap
  - import konfigurasi router ke netbox
  - tambah interface ke netbox dari router
  - tambah ip ke netbox dari router
  - router ke netbox
tools:
  - populate_netbox_from_router
  - get_netbox_device_interfaces
  - get_netbox_device_ips
  - get_netbox_drift_report
  - list_routers
approval_required: true
enabled: true
---

# Prosedur Sinkronisasi Router → NetBox (Interface, VLAN, IP)

## Konteks

Gunakan skill ini ketika router adalah ground truth saat ini dan NetBox belum
lengkap — misalnya saat onboarding router baru, atau saat ada interface/IP di
router yang belum terdokumentasi di NetBox.

**Arah sinkronisasi: Router → NetBox.**
Ini kebalikan dari `netbox-sync` (yang NetBox → Router). Jangan campur keduanya.

Yang dilakukan tool ini:
- Fix parent interface yang salah di NetBox (ambil dari data router)
- Tambah VLAN interface yang ada di router tapi belum ada di NetBox
- Tambah IP address yang ada di router tapi belum ada di NetBox
- Laporkan konflik prefix (alamat sama, prefix beda) — tidak diubah otomatis

Yang **tidak** dilakukan:
- Menghapus data di NetBox yang tidak ada di router
- Mengubah interface yang sudah cocok antara router dan NetBox
- Menangani BGP session — gunakan skill `netbox-bgp-sync` untuk itu

## Parameter `instance`

Default `instance="auto"` — resolves dari field `network` router di config.yaml:
- Router `network: idren` → NetBox IDREN (`ipam.idren.id`)
- Router `network: kampus` → NetBox kampus (`siip.ub.ac.id`)

Override eksplisit hanya jika perlu.

## Langkah Eksekusi

### Langkah 1: Dry-Run — Lihat Rencana Tanpa Eksekusi

```
populate_netbox_from_router(
    router_name="<nama-router>",
    dry_run=True
)
```

Output menampilkan empat kategori:
- **[FIX PARENT]** — interface di NetBox yang parent-nya salah
- **[INTERFACE BARU]** — VLAN interface ada di router, belum di NetBox
- **[IP BARU]** — IP address ada di router, belum di NetBox
- **[KONFLIK PREFIX]** — alamat IP sama tapi prefix beda antara router dan NetBox

Jika semua kategori "Tidak ada" → laporkan ke operator, selesai.

### Langkah 2: Verifikasi Data NetBox Saat Ini (Opsional)

Jika ada ketidakjelasan hasil dry-run, cross-check dengan data NetBox aktual:

```
get_netbox_device_interfaces(device_name="<nama-device-netbox>")
get_netbox_device_ips(device_name="<nama-device-netbox>")
```

### Langkah 3: Presentasikan Rencana ke Operator

Dari hasil dry-run, sajikan ringkasan ke operator:

```
Rencana populate NetBox dari router <nama-router>:

[FIX PARENT] <N> interface:
  - <nama-interface>: parent <lama> → <baru>

[INTERFACE BARU] <N> VLAN interface:
  - vlan-id=<ID>  name=<nama>  parent=<parent>

[IP BARU] <N> IP address:
  - <ip/prefix>  interface=<nama>

[KONFLIK PREFIX] <N> item — tidak akan diubah otomatis:
  - Router: <ip/prefix>  NetBox: <ip/prefix-beda>  interface=<nama>
    → Perlu verifikasi manual di NetBox UI

Total perubahan: <N> fix + <N> interface + <N> IP
Konflik: <N> item perlu penanganan manual

Approval diperlukan sebelum eksekusi.
```

Tunggu konfirmasi operator sebelum lanjut.

### Langkah 4: Eksekusi

Setelah operator setuju:

```
populate_netbox_from_router(
    router_name="<nama-router>",
    dry_run=False
)
```

Sistem akan meminta approval operator via interrupt gate.

Jika NetBox device name berbeda dari nama router di config.yaml, gunakan parameter
`device_name` secara eksplisit:

```
populate_netbox_from_router(
    router_name="<nama-router>",
    device_name="<nama-device-di-netbox>",
    dry_run=False
)
```

### Langkah 5: Verifikasi Pasca Eksekusi

Jalankan dry-run ulang untuk konfirmasi semua item sudah masuk:

```
populate_netbox_from_router(
    router_name="<nama-router>",
    dry_run=True
)
```

Pastikan **[INTERFACE BARU]** dan **[IP BARU]** menunjukkan "Tidak ada."
Jika masih ada sisa → laporkan ke operator beserta detail error dari output eksekusi.

## Penanganan Konflik Prefix

Konflik prefix (alamat IP sama, mask berbeda antara router dan NetBox) tidak
ditangani otomatis karena bisa berarti:
- Router pakai `/30`, NetBox pakai `/29` — salah satu perlu dikoreksi
- Data lama di NetBox yang belum diupdate

Laporkan ke operator dengan detail lengkap dan arahkan ke NetBox UI untuk
koreksi manual: IPAM → IP Addresses → cari alamat → edit prefix length.

## Kasus Khusus

### Auto-Match Device Gagal

Jika tool melaporkan "Auto-match gagal untuk router X":
1. Jalankan `get_netbox_devices()` untuk lihat daftar device dan primary_ip
2. Cari device yang primary_ip-nya cocok dengan host router di config.yaml
3. Gunakan parameter `device_name=<nama>` secara eksplisit

### Parent Interface Tidak Ada di NetBox

Jika dry-run melaporkan "parent tidak ada di NetBox!" untuk interface baru:
- Parent interface fisik (ether/sfp/bond) belum terdaftar di NetBox
- Laporkan ke operator — parent perlu ditambahkan manual di NetBox UI dulu
  sebelum interface virtual bisa dibuat dengan parent yang benar

### Router Belum Ada di config.yaml

Gunakan skill `router-discovery` terlebih dahulu untuk tambahkan router ke
config.yaml, baru jalankan skill ini.

## Validasi Mandiri

Sebelum lapor ke operator, pastikan:
- [ ] Dry-run sudah dijalankan sebelum eksekusi
- [ ] Konflik prefix sudah diidentifikasi dan dilaporkan terpisah
- [ ] Verifikasi dry-run ulang setelah eksekusi — pastikan "Tidak ada" item tersisa

## Handoff

| Kondisi | Aksi | Agent Tujuan |
|---------|------|--------------|
| Sinkronisasi selesai — perlu dokumentasi | Serahkan ringkasan perubahan | document_agent |
| Drift interface/IP masih ada setelah eksekusi | Investigasi error per item | END (lapor operator) |
| BGP session belum di NetBox | Gunakan skill netbox-bgp-sync | netbox_agent (skill: netbox-bgp-sync) |
