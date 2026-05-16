---
name: bgp-diagnostics
domain: routing
triggers:
  - BGP down
  - BGP tidak established
  - internet mati
  - uplink putus
  - BGP session drop
  - prefix hilang dari tabel routing
  - internet tidak bisa diakses
  - cek BGP
  - status BGP
  - BGP jatuh
  - session BGP putus
  - peer BGP tidak konek
  - koneksi IDREN putus
  - link IDREN down
tools:
  - get_bgp_sessions
  - get_routing_full
  - get_router_config
  - get_router_log
  - check_reachability
  - run_command
  - get_system_info
approval_required: false
enabled: true
---

# Diagnosa & Monitoring BGP

## Konteks

Gunakan skill ini untuk cek status BGP atau mendiagnosis masalah BGP. Router edge/gateway
(role `gate_idren`, `edge`, `border`) biasanya menjalankan BGP. Gunakan `list_routers`
untuk melihat role tiap router.

## Prosedur Pengumpulan Data

### Langkah 1: Ambil Status Semua BGP Session
Gunakan `get_bgp_sessions(router_name)` — tool ini mengembalikan SEMUA session dalam format
ringkas tanpa truncation, lengkap dengan state, uptime, prefix count, dan tanda session DOWN.

**JANGAN** gunakan `run_command /routing/bgp/session/print` — outputnya terpotong untuk
router dengan banyak session (>5-6 session).

Output tool berformat:
```
BGP Sessions — GATE-IDREN-UB  Local AS: 64302
Total: 27  Established: 26  Down: 1
────────────────────────────────────────────────────────────────────────────────
  #  St    Type   RemAS  RemoteIP                  Uptime            Pfx  Name
────────────────────────────────────────────────────────────────────────────────
  0  ✓EST  eBGP  141682  2407:940:0:142::1         17w16h38m2s      6123  PEER-GATE-ARENA-PAC-v6-1
  1  ✓EST  eBGP  141682  103.161.244.201            17w16h38m2s     17080  PEER-GATE-ARENA-PAC-1
 23  ✗DWN  eBGP  147171  172.17.0.62               —                   0  PEER-NODE-IDREN-BRIN(BACKUP)-VIA-ICON+-1

⚠ 1 session DOWN:
  - #23 PEER-NODE-IDREN-BRIN(BACKUP)-VIA-ICON+-1  (remote: 172.17.0.62 AS147171)  last-stopped: mar/11/2026 21:17:07
```

### Langkah 2: Kategorikan Session
Dari output `get_bgp_sessions`, kelompokkan session berdasarkan tipe:
- **eBGP upstream**: peer ke ISP atau internet exchange (AS berbeda, prefix count besar — ratusan/ribuan)
  - Contoh: `PEER-GATE-ARENA-PAC-1` dengan 17.080 prefix
- **eBGP nodes**: peer ke universitas/institusi anggota (prefix count kecil, 1-20)
  - Contoh: `PEER-NODE-IDREN-UNEJ-VIA-TELKOM-1` dengan 4 prefix
- **iBGP Route Reflector**: `Type=iBGP` di output tool, biasanya nama `PEER-GATE-...`

**IPv4 vs IPv6**: Pisahkan berdasarkan RemoteIP:
- RemoteIP mengandung `:` (colon) → sesi IPv6 (contoh: `2407:940:0:142::1`, `2001:df6:5a00:7::2`)
- RemoteIP berformat `x.x.x.x` → sesi IPv4
- Prefix count pada sesi IPv6 adalah prefix IPv6, bukan IPv4

### Langkah 3: Analisis Temporal
Perhatikan `uptime` tiap session:
- **Uptime > 1 minggu** → stabil, sebutkan berapa minggu/bulan
- **Uptime 1 hari – 1 minggu** → baru reconnect, bisa normal atau indikasi maintenance/insiden
- **Uptime < 1 hari (< 24 jam)** → ⚠ anomali yang WAJIB dicatat — kapan reconnect, ada di log?
- **Session DOWN** → catat `last-stopped` dari bagian bawah output tool
  - last-stopped baru (hari ini/kemarin) → baru jatuh, perlu investigasi
  - last-stopped lama (minggu/bulan) → kemungkinan sengaja dinonaktifkan

**Definisi ketat "uptime pendek"**: HANYA session dengan uptime < 24h yang masuk kategori ini.
Session dengan uptime 2d, 5d, atau lebih BUKAN "uptime pendek".

### Langkah 4: Identifikasi Pola Primary/Backup
Jika ada dua session ke institusi yang sama (misal: `BRIN(UTAMA)` dan `BRIN(BACKUP)`),
analisis:
- Mana yang aktif, mana yang down
- Apakah backup down saat primary up → wajar (intended failover)
- Apakah keduanya down → masalah serius
- Lihat `last-stopped` pada session DOWN untuk tahu kapan terakhir jatuh

### Langkah 5: Cek Log BGP
Gunakan `get_router_log(router_name, topic="bgp", lines=50)`. Cari:
- `hold timer expired` → keepalive terlambat, link intermittent atau CPU overload
- `connection closed` / `session closed` → kapan terakhir jatuh
- `notification sent/received` + kode error → penyebab spesifik
- `authentication error` → password mismatch
- `Established` berulang kali dalam waktu singkat → flapping

Juga cek `get_router_log(router_name, topic="script", lines=20)` untuk melihat script monitoring
yang aktif. Entri seperti `Host 103.x.x.x is up` menandakan monitoring script berjalan.

### Langkah 6: Cross-reference dengan OSPF
Jika ada masalah routing, cek apakah peer BGP yang bermasalah juga merupakan OSPF neighbor.
Gunakan `get_ospf_neighbors(router_name)` dan bandingkan Router ID/IP:
- BGP established + OSPF Full → routing normal di semua layer
- BGP established + OSPF Init → L3 OK, masalah spesifik di OSPF
- BGP DOWN + OSPF DOWN → kemungkinan masalah link fisik

### Langkah 7: Verifikasi Resource (jika ada indikasi masalah)
Gunakan `get_system_info` hanya jika ada indikasi CPU tinggi atau session flapping.
CPU > 80% bisa menyebabkan keepalive BGP terlambat → hold timer expire.

## Teknik Analisis

### Menghitung Total Prefix — Pisahkan IPv4 dan IPv6

Dari output `get_bgp_sessions`:
- **IPv4 prefix**: jumlahkan kolom `Pfx` dari session dengan RemoteIP tanpa colon (`x.x.x.x`)
- **IPv6 prefix**: jumlahkan kolom `Pfx` dari session dengan RemoteIP mengandung colon (`2001:...`, `2407:...`)
- Jangan mencampurkan keduanya — sesi IPv6 membawa prefix IPv6, bukan IPv4

Contoh:
```
  0  ✓EST  eBGP  141682  2407:940:0:142::1    6123   ← IPv6 prefix
  1  ✓EST  eBGP  141682  103.161.244.201      17080   ← IPv4 prefix
```
Total IPv4 = 17080 (bukan 6123+17080)
Total IPv6 = 6123

### Identifikasi Router/Institusi dari Nama Session
Nama session biasanya mengandung kode institusi:
- `PEER-NODE-IDREN-UNEJ-VIA-TELKOM-1` → node UNEJ via Telkom
- `PEER-GATE-IDREN-ITB-VIA-MORATEL-1` → gateway ITB via Moratel
- `PEER-NODE-IDREN-BRIN(UTAMA)-VIA-ICON+-1` → node BRIN, session utama
- `PEER-GATE-ARENA-PAC-1` → peering ke ARENA-PAC (AS141682)

### Menilai Stabilitas
- Session uptime = beberapa minggu/bulan → stabil
- `last-stopped` ada (bukan kosong) → pernah jatuh, catat tanggalnya
- Banyak session dengan uptime pendek pada waktu bersamaan → ada restart global (maintenance/crash)
- HoldTimer expired berulang + uptime pendek = link WAN tidak stabil

### Konteks Versi RouterOS
Lihat versi RouterOS dari `get_system_info`:
- Hitung usia versi (RouterOS 7.12.1 = Nov 2023 = ~18 bulan pada Mei 2026)
- RouterOS 7.15+ membawa perbaikan stabilitas BGP
- Jika versi > 12 bulan, rekomendasikan upgrade di bagian rekomendasi

## Output yang Diharapkan

**Status:** ✅ [X] established · 🚨 [X] down

## BGP Session Summary

| Router | Upstream | iBGP | Nodes | Total | Status |
|--------|----------|------|-------|-------|--------|
| [nama dari get_bgp_sessions] | [X/Y ✅/🚨] | [X/Y ✅/🚨] | [X/Y ✅/🚨] | [total] | [✅/🚨] |

## Session Down Detail

| Router | Peer | Tipe | Last Stopped | Prefiks | Status |
|--------|------|------|--------------|---------|--------|
| [nama router] | [nama peer dari get_bgp_sessions] | [upstream/ibgp/nodes] | [waktu] | [jumlah] | 🚨 Down |

## Action Items

1. 🚨 **SEGERA** — [tindakan untuk session down]
2. ⚠️ **PERLU** — [monitoring rekomendasi]

*Jika semua normal: "✅ Semua BGP session established."*

## Incident Response: Session Drop

Gunakan bagian ini saat ada laporan "BGP session drop" atau temuan dari morning check.

### Langkah R1: Scope — Cek Semua Router IDREN

Jangan asumsi hanya satu router yang terdampak. Jalankan `get_bgp_sessions` untuk
**semua router** dengan role `gate_idren` dari `list_routers`.

Kelompokkan temuan:
- Router mana yang punya session DOWN
- Apakah session DOWN yang sama muncul di beberapa router → indikasi masalah core

### Langkah R2: Klasifikasi Session yang Drop

Untuk setiap session DOWN, tentukan:

| Klasifikasi | Indikator | Dampak |
|-------------|-----------|--------|
| **ISP Uplink putus** | peer adalah upstream ISP, prefix count besar (ribuan) | Internet ke institusi terdampak |
| **Link antar-IDREN putus** | peer adalah GATE-IDREN-xxx, prefix count kecil (1-20) | Konektivitas bilateral ke node itu |
| **Backup session (intended)** | nama session mengandung `(BACKUP)` dan primary-nya UP | Tidak ada dampak — wajar |
| **Primary dan backup keduanya DOWN** | dua session ke peer yang sama, keduanya DOWN | Koneksi ke institusi itu 100% putus |

**Primary/backup keduanya DOWN → eskalasi segera.**

### Langkah R3: Cek Reachability ke Peer IP

Untuk session DOWN, ambil `RemoteIP` dari output `get_bgp_sessions`.
Jalankan `check_reachability` ke IP tersebut:

- **Tidak reachable** → masalah di L1/L2/L3 — bukan BGP config issue
  → cek apakah circuit di NetBox masih Active, laporkan ke ISP
- **Reachable** → L3 OK, masalah di BGP layer (config, auth, timer)
  → lanjut ke log analysis

### Langkah R4: Log Analysis Terfokus

```
get_router_log(router_name, topic="bgp", lines=100)
```

Interpretasi kode error BGP (Notification):

| Error | Artinya |
|-------|---------|
| `hold timer expired` | keepalive terlambat — link flapping atau CPU tinggi |
| `authentication error` | password MD5 mismatch — cek konfigurasi kedua sisi |
| `cease / administrative reset` | session di-reset manual oleh salah satu pihak |
| `open message error` | mismatch AS number atau router-ID |
| `update message error` | prefix/attribute tidak valid — kemungkinan route leak |

### Langkah R5: Impact Assessment

Setelah identifikasi session yang drop, sampaikan ke operator:

```
IMPACT ASSESSMENT — BGP Session Drop

Session DOWN  : [nama session] di [router]
Tipe          : [ISP uplink / link IDREN / backup]
Peer          : AS[nomor] — [nama institusi/ISP]
Last stopped  : [tanggal waktu dari output tool]
Reachability  : [reachable / tidak reachable ke peer IP]
Penyebab log  : [hold timer / auth error / admin reset / dll]

Dampak        : [deskripsi — misal "koneksi ke NODE-IDREN-ITB via CBN terputus"]
Backup        : [ada dan UP / ada tapi juga DOWN / tidak ada]
Trafik reroute: [ya, via backup / tidak ada backup]
```

### Langkah R6: Eskalasi dan Handoff

Berdasarkan hasil R5, rekomendasikan salah satu:

**Kondisi 1 — Peer tidak reachable (masalah di ISP/link)**
→ Informasikan ke operator untuk hubungi ISP terkait
→ Jika ada backup yang belum aktif otomatis: handoff ke `config_agent` untuk
  enable backup session atau adjust routing policy

**Kondisi 2 — Peer reachable, masalah BGP config**
→ Handoff ke `config_agent` dengan instruksi spesifik (misal: fix password, restart session)
→ JANGAN restart BGP session tanpa konfirmasi operator — berdampak ke routing aktif

**Kondisi 3 — Session backup DOWN, primary UP**
→ Catat saja, tidak perlu tindakan — laporkan sebagai informasional

## Catatan
- RouterOS v7: gunakan `get_bgp_sessions` (wrapper `/routing/bgp/session/print`)
- RouterOS v6: `get_bgp_sessions` otomatis pakai `routing bgp peer print`
- Hold timer default eBGP: 90s. Hold timer agresif (misal 15s): rentan flap di link WAN
- Jangan restart BGP session tanpa konfirmasi NOC — ada dampak ke routing kampus
- Cek semua router gate_idren — jangan asumsi hanya satu yang terdampak


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
| BGP session down — perlu reset/fix konfigurasi | Serahkan perintah + approval | config_agent |
| Prefix leak atau route policy salah | Serahkan analisis + perintah | config_agent |
| Perlu laporan BGP | Serahkan data session | document_agent |
| Semua sehat | Tidak perlu handoff | END |
