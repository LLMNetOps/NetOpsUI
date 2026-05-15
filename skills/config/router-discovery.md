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

Jalankan kembali `check_ssh_access(host=<IP>)` dan periksa SSH banner yang diterima.
MikroTik RouterOS selalu mengirim banner yang dimulai dengan `SSH-2.0-ROSSSH`.
Jika banner mengandung `ROSSSH` → RouterOS confirmed.
Jika banner kosong atau bukan ROSSSH → bukan MikroTik, skip IP ini.

Jika ketiga step sukses → **IP ini VALID** → lanjut ke Fase 4.

Jika semua 3 IP dari NetBox gagal → lanjut ke Fase 3.

---

## Fase 3 — BGP Peer Discovery (Fallback)

Jalankan `list_routers()`, kumpulkan **semua** router dengan `role=gate_idren`.
Ini biasanya GATE-IDREN-UB, GATE-IDREN-UI, GATE-IDREN-ITS, dsb.

**Untuk setiap router gate_idren** (loop satu per satu — jangan berhenti di router pertama):

```
run_command(router_name=<gate_idren_router>, command="/routing/bgp/session/print")
```

Dari output semua session BGP, lakukan dua tahap pencarian:

**Tahap 1 — Cocok nama session:**
Cari session yang namanya mengandung kata kunci router target
(contoh: "ITB", "TO-ITB", "EBGP-ITB", "PEER-ITB").

**Tahap 2 — Jika nama tidak cocok, reasoning dari semua session:**
Baca seluruh daftar session. Pertimbangkan:
- `remote-as` — jika kamu tahu AS number target, cocokkan
- `comment` / `description` field — bisa berisi nama institusi
- `remote-address` — jika masuk subnet yang logis untuk institusi target
  (contoh: ITB sering pakai prefix dari AS45005 atau range tertentu)
- Nama session bisa berformat lain: "PEER-AS45005", "UPL-IDREN-1", dsb.

Jika ada kandidat yang reasonable → catat sebagai `kandidat_bgp` + alasan kenapa dipilih.
Ambil `remote-address` sebagai IP kandidat → jalankan validation chain (Step 2a → 2b → 2c).

**Aturan loop:**
- Jika router gagal SSH (error/timeout) → skip ke router berikutnya
- Jika session ditemukan dan valid → lanjut ke Fase 4
- WAJIB coba semua router gate_idren sebelum menyerah
- Jika sudah coba semua dan tidak ada kandidat → lanjut ke Fase 4 (gagal)

---

## Fase 4 — Laporan ke Operator

### Jika IP valid ditemukan:

Tampilkan ringkasan **setelah** semua validasi selesai. Wajib cantumkan:
- **Apa** yang ditemukan (device, IP, versi ROS)
- **Di mana** ditemukan (sumber data: NetBox atau router mana)
- **Bagaimana** ditemukan (metode: primary_ip, interface IP ke-N, atau BGP session nama X di router Y)

```
Ditemukan dan tervalidasi:

  Device      : GATE-IDREN-ITB
  IP          : 103.xx.xx.xx
  Validasi    : ✓ reachable (RTT: 2.1ms), ✓ SSH port 22 terbuka, ✓ RouterOS banner (SSH-2.0-ROSSSH)
  ROS version : 7

  Cara ditemukan:
    Fase 1  : NetBox [idren] — device GATE-IDREN-ITB ada (29 device total)
    Fase 2  : 3 IP dari NetBox dicoba → semua unreachable (172.17.32.12, 172.21.0.1, 172.21.0.2)
    Fase 3  : BGP session di GATE-IDREN-UI → session "EBGP-TO-ITB" remote-address 103.xx.xx.xx
              Alasan dipilih: nama session mengandung "ITB", remote-as cocok dengan AS ITB

Menambahkan ke config.yaml — menunggu approval operator...
```

Langsung jalankan `add_router_to_config(...)` — interrupt gate akan meminta approval.

Setelah approval dan penambahan berhasil, **langsung lanjutkan** task awal operator
(cek sistem, drift report, dsb.) tanpa menunggu konfirmasi tambahan.

### Jika semua IP gagal validasi:

Laporan lengkap semua yang sudah dicoba — operator harus bisa lihat seluruh jejak pencarian:

```
Tidak berhasil memvalidasi router 'GATE-IDREN-ITB' secara otomatis.

Jejak pencarian:
  Fase 1 — NetBox [idren]:
    → Device GATE-IDREN-ITB ditemukan (atau: tidak ditemukan)
    → primary_ip: kosong (atau: 103.x.x.x → unreachable)

  Fase 2 — IP dari NetBox interface:
    → 172.17.32.12 : ✗ unreachable
    → 172.21.0.1   : ✗ unreachable
    → 172.21.0.2   : ✗ unreachable

  Fase 3 — BGP session di semua router gate_idren:
    → GATE-IDREN-UB : tidak ada session mengandung "ITB", tidak ada kandidat lain yang reasonable
    → GATE-IDREN-UI : SSH timeout — skip
    → GATE-IDREN-ITS: SSH error — skip

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
