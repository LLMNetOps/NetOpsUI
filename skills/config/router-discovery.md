---
name: router-discovery
domain: config
triggers:
  - router tidak ditemukan
  - router tidak dikenal
  - router baru
  - tambah router
  - discover router
  - router belum terdaftar
  - tidak ada di config
tools:
  - list_routers
  - get_netbox_devices
  - get_netbox_device_ips
  - check_reachability
  - check_ssh_access
  - run_command
  - resolve_router_host
  - patch_router_host
  - add_router_to_config
approval_required: true
enabled: true
---

# Router Discovery — Orkestrasi Mandiri dengan Validation Loop

Gunakan skill ini ketika router yang diminta operator tidak ada di config.yaml.

**Aturan utama**: Jangan lapor ke operator sampai IP sudah tervalidasi penuh.
Lakukan semua pencarian dan validasi secara mandiri terlebih dahulu.

---

## Fase 1 — Kumpulkan IP Kandidat dari NetBox

Jalankan `get_netbox_devices(instance="idren")` (atau `"kampus"` sesuai konteks).

Cari device yang namanya cocok atau mengandung kata kunci dari permintaan operator
(contoh: "ITB", "ITS", "UNESA", "UNPATTI").

Jika device ditemukan, ambil IP kandidat dalam urutan prioritas:
1. `primary_ip` dari data device
2. IP dari `get_netbox_device_ips(device_name=<nama>)` — ambil maksimal 3 IP

Simpan daftar: `kandidat_ip = [primary_ip, ip2, ip3]`

Jika device **tidak ditemukan** di NetBox → langsung ke **Fase 3**.

---

## Fase 2 — Validation Loop (max 3 IP dari NetBox)

Untuk setiap IP di `kandidat_ip`, jalankan validation chain secara berurutan:

### Step 2a — Reachability
```
check_reachability(host=<IP>)
```
Jika gagal (timeout/unreachable) → skip ke IP berikutnya.

### Step 2b — SSH Access
```
check_ssh_access(host=<IP>)
```
Jika port 22 tidak respond → skip ke IP berikutnya.

### Step 2c — RouterOS Confirm
```
run_command(router_name=<nama_terdekat_di_config>, command="/system/resource/print")
```

Catatan: karena router belum ada di config, gunakan tool `check_reachability` dengan
parameter `host=<IP>` langsung, bukan `router_name`. Untuk ROS confirm, pakai SSH
manual via `check_ssh_access` dan observasi banner-nya.

Jika ketiga step sukses → **IP ini VALID** → lanjut ke Fase 4.

Jika semua 3 IP dari NetBox gagal → lanjut ke Fase 3.

---

## Fase 3 — BGP Peer Discovery (Fallback)

SSH ke router IDREN yang sudah terdaftar dan valid di config.yaml
(gunakan `list_routers()` untuk daftar, cari yang `role=gate_idren`).

Jalankan:
```
run_command(router_name="GATE-IDREN-UB", command="/routing/bgp/session/print")
```

Cari session BGP yang namanya mengandung kata kunci router target
(contoh: session "EBGP-ITB-1" untuk target "ITB").

Ambil `remote_addr` dari session tersebut sebagai IP kandidat baru.

Jalankan validation chain (Step 2a → 2b → 2c) untuk IP dari BGP peer.

Jika valid → lanjut ke Fase 4.

Jika tidak valid → lanjut ke Fase 4 (gagal — tanya operator).

---

## Fase 4 — Laporan ke Operator

### Jika IP valid ditemukan:

Tampilkan ringkasan **setelah** semua validasi selesai:

```
Ditemukan dan tervalidasi:
  Device      : GATE-IDREN-ITB
  IP          : 103.xx.xx.xx  ✓ reachable, SSH OK, RouterOS confirmed
  Sumber      : NetBox primary_ip / BGP peer GATE-IDREN-UB session EBGP-ITB-1
  Role        : gate_idren
  Network     : idren
  ROS version : 7

Menambahkan ke config.yaml — menunggu approval operator...
```

Langsung jalankan `add_router_to_config(...)` — interrupt gate akan meminta approval.

Setelah approval dan penambahan berhasil, **langsung lanjutkan** task awal operator
(cek sistem, drift report, dsb.) tanpa menunggu konfirmasi tambahan.

### Jika semua IP gagal validasi:

Laporan singkat ke operator dengan semua yang sudah dicoba:

```
Tidak berhasil memvalidasi router 'GATE-IDREN-ITB' secara otomatis.

Dicoba:
  - NetBox primary_ip: 103.x.x.x → tidak reachable
  - NetBox interface IP: 172.x.x.x → SSH refused
  - BGP peer GATE-IDREN-UB (session EBGP-ITB-1): 103.x.x.x → timeout

Mohon berikan IP management router ini secara manual:
  host (IP)   : ?
  ros_version : 6 atau 7?
```

Setelah operator berikan IP, jalankan validation chain sekali lagi.
Jika valid, lanjut ke `add_router_to_config` dengan approval.

---

## Catatan Implementasi

- **Jangan tanya operator di tengah proses** — selesaikan semua Fase 1-3 dulu
- **Jangan lapor progress per-step** — operator hanya perlu tahu hasil akhir
- Jika satu IP gagal di Step 2a, langsung skip ke IP berikutnya tanpa komentar
- ROS version: deteksi dari output `/system/resource/print`
  - Ada field `version:` → ambil angka major (6 atau 7)
  - Jika tidak bisa deteksi → default 7
- Setelah `add_router_to_config` sukses, config di-reload otomatis — tidak perlu restart


## Validasi Mandiri

Sebelum lapor ke operator, pastikan:
- [ ] Data dikumpulkan dari semua sumber relevan
- [ ] Temuan dikonfirmasi dengan minimal 2 data point (bukan hanya 1 tool)
- [ ] Anomali: bandingkan dengan baseline atau history sebelum simpulkan masalah
- [ ] Jika ada kegagalan tool (SSH timeout, error): coba router/interface alternatif dulu

Jika validasi belum lengkap → coba sumber alternatif, baru lapor jika memang tidak bisa resolve.

## Handoff

| Kondisi | Aksi | Agent Tujuan |
|---------|------|--------------|
| Router ditemukan + tervalidasi + ditambahkan | Lanjutkan task awal operator | agent semula (monitor/diagnose) |
| Gagal validasi semua IP | Tanya operator IP manual, tunggu input | END (tunggu operator) |
