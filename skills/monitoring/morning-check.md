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
tools:
  - list_routers
  - check_reachability
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

Pengecekan cepat kondisi jaringan IDREN di awal shift. Target selesai < 5 menit.
Fokus pada GATE-IDREN-UB dan koneksi antar-node IDREN — bukan semua router kampus.

Output: satu blok ringkasan yang bisa langsung dilaporkan ke tim atau manajemen.

## Prosedur

### Langkah 1: Reachability Semua GATE-IDREN Node

Gunakan `check_reachability` untuk semua router dengan `role=gate_idren`.
Dari `list_routers`, filter by role atau nama yang mengandung `GATE-IDREN`.

Threshold:
- Tidak merespons → ✗ KRITIS
- Latency > 100ms → ⚠ LAMBAT

### Langkah 2: Status BGP Session

Untuk GATE-IDREN-UB (router lokal), jalankan `get_bgp_sessions("GATE-IDREN-UB")`.

Cek:
- Session `established` → ✓
- Session `down` / `idle` → ✗ — catat peer name dan ISP yang terdampak
- Prefix count turun > 50% dari biasanya → ⚠ — kemungkinan route leak atau filter masalah

### Langkah 3: Anomali Traffic

Jalankan `get_top_interfaces_all` untuk melihat utilisasi tertinggi di semua router.

Flag:
- Interface uplink > 80% utilisasi → ⚠ HAMPIR PENUH
- Interface uplink > 95% utilisasi → ✗ CONGESTED
- Interface yang seharusnya aktif tapi 0 traffic → ⚠ cek kondisi

### Langkah 4: Log Error 24 Jam Terakhir

Jalankan `get_router_log("GATE-IDREN-UB", lines=100)` untuk melihat event sejak kemarin.

Cari:
- `critical` atau `error` → catat dan flag
- `interface changed state` berulang → link flapping
- BGP `state changed` → instabilitas routing
- `login failure` berulang → indikasi serangan brute force

Cukup log GATE-IDREN-UB untuk morning check — router kampus lain cek jika ada tanda masalah.

### Langkah 5: Drift NetBox vs Router

Jalankan `get_netbox_drift_report("GATE-IDREN-UB")`.

Interpretasi:
- Tidak ada drift → ✓ NetBox sinkron
- Ada drift → ⚠ catat item yang berbeda, tapi JANGAN eksekusi perubahan di sini
  (drift fix adalah task terpisah, butuh approval operator)

## Format Output

Tampilkan hasil dalam format ini — satu blok, ringkas:

```
MORNING CHECK — [tanggal] [jam WIB]
══════════════════════════════════════════════════════
REACHABILITY : [X] node up / [Y] node down
               ✗ DOWN: [nama node jika ada]

BGP SESSION  : [X] established / [Y] down
               ✗ DOWN: [peer-name] via [ISP] — [router]
               ⚠ PREFIX: [peer] prefix count turun [X → Y]

TRAFFIC      : puncak tertinggi [X]% di [interface] ([router])
               ⚠ CONGESTED: [interface] [X]% jika ada

LOG (24 jam) : [bersih / X event kritis]
               ⚠ [ringkasan singkat event jika ada]

NETBOX DRIFT : [sinkron / X item drift]
               ⚠ [ringkasan singkat drift jika ada]

──────────────────────────────────────────────────────
STATUS: ✓ NORMAL | ⚠ PERLU PERHATIAN | ✗ ADA MASALAH AKTIF
```

## Action Items

Setelah ringkasan, tambahkan action items jika ada:

```
ACTION ITEMS:
1. [item kritis — selesaikan hari ini]
2. [item perhatian — monitor]
```

Jika tidak ada masalah, cukup tulis: "Tidak ada action item — jaringan normal."

## Catatan

- Morning check TIDAK mengeksekusi perubahan apapun — hanya observasi dan laporan.
- Untuk drill-down lebih dalam ke BGP → gunakan skill `bgp-diagnostics`.
- Untuk drill-down traffic → skill `network-traffic-analysis`.
- Untuk fix drift NetBox → route ke `netbox_agent` (budi).
- Jika operator minta laporan disimpan ke file → handoff ke `document_agent`.
