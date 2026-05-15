---
name: ospf-diagnostics
domain: routing
triggers:
  - OSPF neighbor down
  - adjacency hilang
  - routing OSPF bermasalah
  - OSPF tidak full
  - OSPF state bukan full
  - routing berubah tiba-tiba
  - subnet tidak reachable
  - cek OSPF
  - status OSPF
tools:
  - get_ospf_neighbors
  - get_routing_full
  - get_router_config
  - get_router_log
  - get_bgp_sessions
  - check_reachability
  - run_command
approval_required: false
enabled: true
---

# Diagnosa & Monitoring OSPF

## Konteks

Gunakan skill ini untuk cek status OSPF atau mendiagnosis masalah adjacency. Router gateway
dan backbone biasanya menjalankan OSPF sebagai interior routing protocol.

## Prosedur Pengumpulan Data

### Langkah 1: Ambil Status Semua OSPF Neighbor
Gunakan `get_ospf_neighbors(router_name)` — mengembalikan semua neighbor dengan state,
Router ID, adjacency uptime, **state-changes (kolom SC)**, dan area.

**JANGAN** gunakan `run_command /routing/ospf/neighbor/print` sebagai pengganti — output
tidak selalu lengkap dan bisa terpotong.

Output tool berformat:
```
OSPF Neighbors — GATE-IDREN-UB
Total: 7  Full: 6  Masalah: 1
────────────────────────────────────────────────────────────────────────────────
  #  State     Address             RouterID              SC  Adjacency         Area
────────────────────────────────────────────────────────────────────────────────
  0  ✓Full     172.31.0.30         103.78.233.3          21  8w2d15h48m7s      ospf-area-0
  1  ⚠Init     103.78.235.0        172.16.32.9            1  —                 ospf-area-0
  4  ✓Full     172.31.0.38         192.168.88.1          35  5d15h26s          ospf-area-0

⚠ Neighbor tidak FULL:
  - #1 103.78.235.0 (RouterID: 172.16.32.9) state=Init state-changes=1 adjacency=—

⚠ Neighbor Full tapi state-changes tinggi (>20) — riwayat instabilitas:
  - #0 172.31.0.30 (RouterID: 103.78.233.3) state-changes=21 adjacency=8w2d...
  - #4 172.31.0.38 (RouterID: 192.168.88.1) state-changes=35 adjacency=5d...
```

### Langkah 2: Analisis State Tiap Neighbor
- `Full` → normal, adjacency terbentuk
- `2-Way` → neighbor terlihat tapi adjacency tidak naik (biasanya DROTHER di broadcast network)
- `ExStart`/`Exchange`/`Loading` → proses naik, jika stuck > beberapa menit ada masalah
- `Init` → router menerima Hello dari peer tapi peer tidak menerima Hello dari router ini
- `Down` → tidak ada Hello yang diterima sama sekali

### Langkah 3: Analisis Kolom SC (State-Changes)
Kolom `SC` menunjukkan berapa kali state adjacency berubah sejak router boot:
- **1** → neighbor stuck di Init/2-Way dan **belum pernah berhasil** membentuk adjacency Full
- **6-10** → normal (beberapa maintenance/reboot dalam riwayat)
- **> 20** → riwayat instabilitas — link atau konfigurasi bermasalah
  - Meski state sekarang Full, sc > 20 wajib dicatat sebagai anomali
  - Bandingkan antar neighbor: outlier yang jauh di atas rata-rata perlu perhatian
  - Contoh: rata-rata 7, tapi ada satu neighbor dengan sc=35 → sangat mencurigakan

**Tool sudah memflag** neighbor dengan sc > 20 di bagian bawah output dengan keterangan
"Neighbor Full tapi state-changes tinggi".

### Langkah 4: Cross-reference dengan BGP — Identifikasi Router
Ini langkah kritis yang sering diabaikan. Untuk neighbor yang bermasalah (tidak Full):

1. Ambil `get_bgp_sessions(router_name)` pada router yang sama
2. **Cocokkan dua cara**:
   - Apakah `Address` neighbor OSPF cocok dengan `RemoteIP` di BGP session? → identifikasi langsung
   - Apakah `RouterID` neighbor OSPF cocok dengan `RemoteIP` di BGP session? → bisa terjadi di iBGP
3. Jika ditemukan BGP session yang cocok:
   - Lihat kolom `Name` di BGP session → nama mengandung kode institusi
   - Contoh: OSPF address `103.78.235.0` cocok BGP `PEER-GATE-IDREN-JATINEGARA-VIA-TELKOM-1` → ini GATE-JATINEGARA

**Interpretasi setelah cross-reference:**
- **OSPF Init + BGP Established** → konektivitas L3 berfungsi, masalah spesifik di OSPF
  (konfigurasi, MTU, authentication). BUKAN masalah link fisik.
  → tulis: "BGP ke peer ini established (iBGP #7 JATINEGARA), artinya L3 OK. Masalah ada di konfigurasi OSPF."
- **OSPF Init + BGP tidak ada / DOWN** → kemungkinan masalah link atau subnet tidak routable
- **OSPF Full + BGP DOWN** → routing berjalan, masalah di layer BGP saja

### Langkah 5: Cek Log OSPF
Gunakan `get_router_log(router_name, topic="ospf", lines=50)`. Cari:
- `neighbor changed state` → kapan dan dari state apa
- `authentication failure` → mismatch key/password
- `dead timer expired` → Hello tidak diterima dalam dead interval
- Jika log OSPF kosong tapi neighbor stuck Init → neighbor mungkin tidak pernah mengirim Hello
  (artinya masalah ada di sisi remote, bukan di router ini)

### Langkah 6: Verifikasi Konfigurasi (jika perlu)
Jika tidak ada log yang membantu, gunakan `get_router_config(router_name, section="routing-ospf")`:
- Area ID — harus sama di kedua sisi
- Hello/dead interval — default 10s/40s, harus cocok
- Authentication — jika digunakan, type dan key harus identik di kedua sisi
- Interface template — pastikan interface yang benar sudah di-assign ke OSPF

## Teknik Analisis

### Membaca State-Changes dalam Konteks
Adjacency yang baru berumur 5 hari dengan state-changes=35 mengindikasikan:
- Router baru reconnect ~5 hari lalu
- Sebelumnya mengalami 35x flap (sangat tidak stabil)
- Bisa jadi hardware, link fisik, atau timer mismatch
- Ini WAJIB dicatat meski state sekarang Full

Adjacency berumur beberapa minggu dengan state-changes=6-7 adalah normal.

### Membedakan "Belum Pernah Naik" vs "Sedang Flapping"
- state=Init, state-changes=1, adjacency=— → **belum pernah** established sejak router boot
- state=Full, state-changes=35, adjacency=5d → **pernah** flapping parah, sekarang stabil tapi perlu monitoring
- state=Init, state-changes=5 → pernah naik beberapa kali, sekarang jatuh lagi

### Identifikasi Institusi dari Router ID
Router ID biasanya mencerminkan loopback atau IP manajemen institusi. Cara identifikasi:
1. Cek apakah Router ID muncul sebagai RemoteIP di BGP session (metode paling cepat)
2. Cek nama BGP session yang cocok → nama mengandung kode institusi
3. Contoh: RouterID `103.78.233.3` = `103.78.233.3` di BGP iBGP session GATE-ITB

### Dampak Terhadap Routing
OSPF yang tidak Full belum tentu mempengaruhi traffic jika ada BGP yang berjalan di link
yang sama. Selalu nyatakan dampak aktual:
- "konektivitas ke {peer} tetap berjalan via BGP (iBGP #7 established), anomali OSPF ini tidak mempengaruhi traffic saat ini"
- Hindari "OSPF Init, perlu investigasi" tanpa menyebutkan dampak aktual

## Output yang Diharapkan

Laporan OSPF yang mencakup:
1. Jumlah total neighbor dan breakdown Full/tidak Full
2. Tabel semua neighbor dengan state, adjacency uptime, dan **state-changes**
3. Untuk tiap neighbor tidak Full:
   - Identitas neighbor (dari cross-reference BGP atau Router ID)
   - Analisis state-changes (baru atau lama, flapping atau belum pernah naik)
   - Hasil cross-reference dengan BGP
   - Kemungkinan penyebab berdasarkan bukti
4. **Neighbor dengan state-changes > 20 meski sekarang Full** (flagged oleh tool) — wajib dicatat
5. Rekomendasi spesifik dengan perintah RouterOS

## Catatan
- RouterOS v7: gunakan `get_ospf_neighbors` (wrapper `/routing/ospf/neighbor/print`)
- RouterOS v6: `get_ospf_neighbors` otomatis pakai `routing ospf neighbor print`
- OSPF menggunakan IP protocol 89 (bukan TCP/UDP) — firewall yang memblokir protocol 89
  menyebabkan neighbor stuck di Init
- MTU mismatch menyebabkan OSPF DBD/LSA di-drop — neighbor bisa stuck di ExStart/Exchange
- state-changes=0 setelah boot normal → OSPF baru start dan belum pernah ada perubahan state


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
| OSPF neighbor down atau adjacency flapping | Serahkan perintah debug + fix | config_agent |
| Cost/metric perlu disesuaikan | Serahkan perintah + approval | config_agent |
| Semua neighbor normal | Tidak perlu handoff | END |
