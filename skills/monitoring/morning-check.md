---
name: morning-check
domain: monitoring
triggers:
  - morning check
  - cek pagi
  - pengecekan pagi
  - status pagi
  - briefing pagi
  - good morning check
  - laporan pagi
  - mulai kerja cek dulu
  - kondisi jaringan pagi ini
  - morning check idren
  - morning check kampus
  - cek pagi idren
  - cek pagi kampus
tools:
  - list_routers
  - check_reachability
  - get_system_info
  - get_bgp_sessions
  - get_top_interfaces_all
  - get_router_log
  - get_netbox_drift_report
  - get_current_time
approval_required: false
enabled: true
---

# Morning Check — Pengecekan Rutin Pagi Hari

## Konteks

Pengecekan cepat kondisi seluruh jaringan — kampus dan IDREN — di awal shift.
Target selesai < 5 menit. Output: satu blok ringkasan yang bisa langsung dilaporkan.

Cakupan:
- **Router kampus** (role: `access`, `backbone`) — reachability + resource
- **Router IDREN** (role: `gate_idren`) — reachability + BGP + traffic + log + drift NetBox

## Scope Check

Sebelum mulai, tentukan scope dari permintaan operator:

| Kata kunci dalam permintaan | Scope |
|-----------------------------|-------|
| "idren" | Hanya role `gate_idren` |
| "kampus" | Hanya role `backbone` + `access` |
| "backbone" | Hanya role `backbone` |
| "access" | Hanya role `access` |
| Tidak ada kata kunci scope | Semua role (default) |

Contoh:
- "morning check" → semua router
- "cek pagi IDREN" → hanya gate_idren
- "morning check kampus" → backbone + access saja

## Aturan Kritis — Wajib Dibaca Sebelum Mulai

**JANGAN tulis output atau ringkasan sebelum SEMUA langkah berikut selesai dieksekusi:**

| Langkah | Tool yang WAJIB dipanggil | Selesai? |
|---------|--------------------------|----------|
| 0 | `recall_all_router_facts`, `list_routers` | — |
| 1 | `check_reachability` untuk setiap router dalam scope | — |
| 2 | `get_system_info` untuk router backbone/access yang reachable | — |
| 3 | `get_bgp_sessions` untuk setiap router gate_idren | — |
| 4 | `get_top_interfaces_all` | — |
| 5 | `get_router_log` untuk setiap router IDREN (dan kampus jika ada anomali) | — |
| 6 | `get_netbox_drift_report` untuk setiap router gate_idren | — |

**LARANGAN KERAS:**
- JANGAN tulis "N/A (belum cek...)" — jika belum dikerjakan, kerjakan dulu
- JANGAN tulis action items untuk langkah yang belum dilakukan — lakukan langkah itu sekarang
- JANGAN berhenti di tengah prosedur dan menulis ringkasan parsial
- JANGAN cetak teks dari bagian "Format Output" sebelum semua tool selesai — format itu HANYA template struktur, bukan output yang harus dicetak
- SEMUA nilai dalam tabel output HARUS berasal dari hasil tool call aktual. DILARANG mengisi tabel dengan tebakan, estimasi, atau nilai karangan. Kolom tanpa data dari tool → tulis `—`.

Jika scope IDREN saja: skip Langkah 2 (resource kampus), tapi Langkah 0,1,3,4,5,6 WAJIB semua.

## Prosedur

### Langkah 0: Cek Memory + Dapatkan Daftar Router

Mulai dengan `recall_all_router_facts()` — lihat apa yang sudah diketahui dari sesi sebelumnya.
Perhatikan router yang pernah unreachable atau punya catatan masalah — prioritaskan pengecekan.

Lanjut dengan `list_routers()`. Filter berdasarkan scope yang ditentukan di atas.

Kelompokkan hasil filter:
- `gate_idren` → cek penuh: reachability + BGP + traffic + log + drift NetBox
- `backbone`, `access` → cek dasar: reachability + resource

Tidak ada hardcode nama router — semua dinamis dari daftar ini.

**→ LANGKAH 0 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL check_reachability untuk setiap router dalam scope.**

### Langkah 1: Reachability Semua Router

Jalankan `check_reachability` untuk setiap router dari daftar.

Threshold:
- Tidak merespons → ✗ KRITIS
- Latency > 100ms → ⚠ LAMBAT

Catat: berapa total router up vs down, pisahkan antara router kampus dan router IDREN.

**→ LANGKAH 1 SELESAI. JANGAN TULIS APAPUN. Jika scope termasuk kampus: LANGSUNG PANGGIL get_system_info. Jika scope IDREN saja: LANGSUNG PANGGIL get_bgp_sessions untuk setiap router gate_idren.**

### Langkah 2: Resource Router Kampus yang Aktif

Untuk router role `backbone` dan `access` yang reachable, jalankan `get_system_info`.

Flag:
- CPU > 80% → ⚠
- Memory > 90% → ⚠
- Uptime < 10 menit → ✗ baru restart — cari penyebab

Jika semua normal, cukup tulis "resource normal". Jangan tampilkan detail tiap router
jika tidak ada anomali — ringkasan saja.

**→ LANGKAH 2 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_bgp_sessions untuk setiap router gate_idren.**

### Langkah 3: BGP Session — Semua Router IDREN

Untuk setiap router dengan role `gate_idren`, jalankan `get_bgp_sessions(router_name)`.

Cek per router:
- Session `established` → ✓
- Session `down` / `idle` → ✗ — catat peer name dan ISP yang terdampak
- Prefix count nol atau turun > 50% → ⚠ kemungkinan route leak / filter masalah

**LARANGAN**: Setelah Langkah 3 selesai, JANGAN panggil `get_bgp_sessions` lagi di langkah manapun.
Data BGP sudah lengkap di sini. Jika log (Langkah 5) menunjukkan event BGP,
gunakan data yang sudah ada di context — bukan fetch ulang.

**→ LANGKAH 3 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_top_interfaces_all dengan filter roles sesuai scope.**

### Langkah 4: Anomali Traffic

Jalankan `get_top_interfaces_all` dengan filter `roles` sesuai scope:

| Scope | Perintah |
|-------|---------|
| IDREN | `get_top_interfaces_all(roles="gate_idren")` |
| Kampus | `get_top_interfaces_all(roles="backbone,access")` |
| Semua | `get_top_interfaces_all()` |

Flag:
- Interface uplink > 80% → ⚠ HAMPIR PENUH
- Interface uplink > 95% → ✗ CONGESTED
- Interface yang seharusnya aktif tapi 0 traffic → ⚠

**→ LANGKAH 4 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_router_log untuk setiap router gate_idren.**

### Langkah 5: Log Error 24 Jam Terakhir

Untuk setiap router IDREN (role `gate_idren`), jalankan `get_router_log(router_name, lines=50)`.

Cari:
- `critical` atau `error` → flag
- `interface changed state` berulang → link flapping
- BGP `state changed` → instabilitas routing
- `login failure` berulang → indikasi brute force

Untuk router kampus: cek log hanya jika ada anomali di langkah 1 atau 2.

**→ LANGKAH 5 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_netbox_drift_report untuk setiap router gate_idren.**

### Langkah 6: Drift NetBox vs Router

Untuk setiap router IDREN (role `gate_idren`), jalankan:

```
get_netbox_drift_report(router_name=<nama>)
```

Parameter `instance` default `"auto"` — resolves otomatis dari field `network` di config.yaml.
Router dengan `network: idren` → query NetBox IDREN (`ipam.idren.id`).
Router dengan `network: kampus` → query NetBox kampus (`siip.ub.ac.id`).
Tidak perlu set manual.

Interpretasi:
- Tidak ada drift → ✓
- Ada drift → ⚠ catat item, tapi JANGAN eksekusi perubahan di sini

Router kampus tidak perlu drift check — NetBox hanya tracking device IDREN untuk sekarang.

**→ LANGKAH 6 SELESAI. SEMUA DATA TERKUMPUL. SEKARANG TULIS LAPORAN MORNING CHECK.**

## Format Output

INSTRUKSI: Tulis output ini HANYA setelah Langkah 0–6 selesai semua.
Setiap nilai dalam tabel harus dari tool result. Satu baris per router.

---

**MORNING CHECK — [tanggal dari get_current_time()] [jam WIB]**
**Scope:** [SEMUA | IDREN | KAMPUS | BACKBONE | ACCESS]
**Status:** ✅ [jumlah] normal · ⚠️ [jumlah] perhatian · 🚨 [jumlah] kritis

---

## Reachability

*(Isi satu baris per router dari hasil check_reachability — nama dan latency dari tool result)*

| Router | Role | Status | Latency |
|--------|------|--------|---------|
| [nama dari list_routers] | [role] | ✅ Up / 🚨 Down | [ms dari tool] |

## Resource Kampus *(skip jika scope IDREN)*

*(Isi dari hasil get_system_info — skip jika semua normal)*

| Router | CPU | Memory | Uptime | Status |
|--------|-----|--------|--------|--------|
| [nama router] | [CPU%] | [Mem%] | [uptime] | ✅/⚠️/🚨 |

## BGP Session

*(Isi dari hasil get_bgp_sessions — satu baris per router, angka dari tool result)*

| Router | Established | Down | Peer Down | Status |
|--------|-------------|------|-----------|--------|
| [nama router] | [jumlah established] | [jumlah down] | [nama peer atau —] | ✅/🚨 |

*Jika ada session down: sebutkan nama peer, jumlah prefiks, dan durasi down dari tool result.*

## Traffic Puncak

*(Isi dari hasil get_top_interfaces_all — jika tidak ada data: tulis "Tidak ada data traffic")*

| Interface | Router | Utilisasi | Status |
|-----------|--------|-----------|--------|
| [nama interface] | [nama router] | [%] | ✅/⚠️/🚨 |

## Log 24 Jam

*(Isi dari hasil get_router_log — satu baris per router)*

| Router | Event | Jumlah | Status |
|--------|-------|--------|--------|
| [nama router] | [jenis event atau —] | [jumlah atau 0] | ✅ Bersih / 🚨 |

## NetBox Drift *(skip jika scope kampus)*

*(Isi dari hasil get_netbox_drift_report — satu baris per router)*

| Router | Drift Item | Jumlah | Status |
|--------|-----------|--------|--------|
| [nama router] | [item drift atau —] | [jumlah atau 0] | ✅ Sinkron / ⚠️ |

---

## Action Items

*Jika tidak ada masalah: "✅ Tidak ada action item — jaringan normal."*

Jika ada masalah (hanya berdasarkan temuan dari tool result, BUKAN asumsi):

1. 🚨 **SEGERA** — [tindakan spesifik berdasarkan temuan konkret]
2. ⚠️ **PERLU** — [tindakan penting berdasarkan temuan konkret]
3. 💡 **OPSIONAL** — [rekomendasi improvement berdasarkan data]

## Catatan

- Bagian output yang tidak relevan dengan scope di-skip sepenuhnya.
  Contoh: scope IDREN → bagian "RESOURCE (kampus)" tidak ditampilkan.
  Contoh: scope kampus → bagian "BGP SESSION" dan "NETBOX DRIFT" tidak ditampilkan.
- Morning check hanya observasi — tidak ada eksekusi perubahan.
- Drill-down BGP → skill `bgp-diagnostics`.
- Drill-down traffic → skill `network-traffic-analysis`.
- Fix drift NetBox → route ke `netbox_agent` (budi).
- Simpan laporan ke file → handoff ke `document_agent`.


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
| Ada router unreachable atau link down | Serahkan detail + instruksi diagnosa | diagnose_agent |
| Ada perubahan konfigurasi perlu dieksekusi | Serahkan perintah spesifik + approval | config_agent |
| Ada drift NetBox vs router | Serahkan router_name + instance | netbox_agent |
| Semua normal atau setelah analisis selesai | Buat laporan morning check | document_agent |
| Tidak ada temuan kritis | Tidak perlu handoff | END |
