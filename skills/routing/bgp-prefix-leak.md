---
name: bgp-prefix-leak
domain: routing
triggers:
  - kebocoran prefix
  - prefix leak
  - prefix bocor
  - filter BGP salah
  - prefix filter hilang
  - as-path filter
  - route yang tidak seharusnya masuk
  - prefix tidak seharusnya diterima
  - prefix tidak seharusnya diiklankan
  - advertise prefix salah
  - routing anomali
tools:
  - get_bgp_sessions
  - get_routing_full
  - get_router_config
  - get_router_log
  - run_command
  - list_routers
approval_required: false
enabled: true
---

# Diagnosa Kebocoran Prefix BGP

## Konteks

Kebocoran prefix (prefix leak) terjadi ketika:
1. Router menerima prefix yang seharusnya diblok oleh filter
2. Router mengiklankan prefix yang tidak seharusnya (misal prefix internal bocor ke internet)
3. Filter tidak ada sama sekali untuk session tertentu

Di jaringan IDREN, ini sangat kritis karena bisa memengaruhi routing seluruh jaringan
riset dan pendidikan Indonesia.

## Tipe Kebocoran

| Tipe | Deskripsi | Risiko |
|------|-----------|--------|
| **Inbound leak** | Menerima prefix yang tidak seharusnya dari peer | Routing tidak optimal, trafik hijacking |
| **Outbound leak** | Mengiklankan prefix yang tidak seharusnya ke peer | Trafik orang lain lewat kita, blackhole |
| **Missing filter** | Session tidak punya filter sama sekali | Terima/kirim semua prefix tanpa seleksi |
| **Wrong AS-path** | AS-path filter tidak sesuai — terlalu longgar atau terlalu ketat | Blok prefix yang valid atau terima yang tidak valid |

## Prosedur Deteksi

### Langkah 1: Identifikasi Session Tanpa Filter

Gunakan `run_command` dengan perintah berikut untuk setiap router IDREN:

```
/routing/bgp/session/print detail
```

Cari session yang tidak punya `input.filter` atau `output.filter` terisi.
Session tanpa filter → semua prefix diterima/dikirim tanpa seleksi → potensi leak.

### Langkah 2: Cek Isi Routing Table — Prefix Anomali

```
get_routing_full(router_name)
```

Flag prefix yang mencurigakan:
- Prefix internal (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) muncul di BGP table
  dengan next-hop yang bukan router lokal → kemungkinan bocor dari peer
- Prefix dengan AS-path yang sangat panjang (> 8 hop) → indikasi route tidak efisien
  atau trafik di-reroute tidak wajar
- Prefix duplikat dengan dua sumber berbeda → bisa menyebabkan routing instabilitas

### Langkah 3: Audit Prefix List dan Filter

Gunakan `get_router_config(router_name)` atau `run_command` untuk cek:

**Cek prefix-list yang ada:**
```
/routing/filter/rule/print
```

**Cek apakah session menggunakan filter:**
```
/routing/bgp/session/print detail where input.filter=""
```
Output tidak kosong → ada session tanpa input filter.

```
/routing/bgp/session/print detail where output.filter=""
```
Output tidak kosong → ada session tanpa output filter.

### Langkah 4: Cek Log untuk Anomali Prefix

```
get_router_log(router_name, topic="bgp", lines=100)
```

Cari:
- `update message error` → peer kirim prefix/attribute tidak valid
- Lonjakan prefix count mendadak (dari `get_bgp_sessions` — bandingkan dengan baseline)
- Session yang naik-turun berulang setelah menerima update tertentu

### Langkah 5: Bandingkan Prefix Count dengan Baseline

Dari `get_bgp_sessions`, bandingkan prefix count tiap session:

| Tipe session | Baseline normal | Flag jika |
|--------------|-----------------|-----------|
| eBGP ke ISP/upstream | ribuan prefix (5k–800k) | > 2x normal atau < 100 tiba-tiba |
| eBGP ke node IDREN | 1–20 prefix | > 50 tiba-tiba |
| iBGP Route Reflector | variasi | turun drastis |

Lonjakan besar di node IDREN → node itu mungkin bocorkan prefix tambahan.
Turun drastis di upstream → filter terlalu ketat atau peer reset.

## Format Laporan

```
AUDIT PREFIX LEAK — [router] — [tanggal]
══════════════════════════════════════════════════════

SESSION TANPA FILTER:
  [nama session] — tidak ada input.filter
  [nama session] — tidak ada output.filter
  ✓ Semua session sudah memiliki filter (jika bersih)

PREFIX ANOMALI DI ROUTING TABLE:
  [prefix] via [AS] — [alasan dicurigai]
  ✓ Tidak ada anomali (jika bersih)

PREFIX COUNT ANOMALI:
  [session] — baseline ~[X], sekarang [Y] — ⚠ lonjakan/penurunan
  ✓ Semua prefix count normal (jika bersih)

FILTER AUDIT:
  Total filter rules: [X]
  Session tanpa filter: [X] session
  [detail jika ada masalah]

──────────────────────────────────────────────────────
KESIMPULAN: BERSIH | ⚠ PERLU REVIEW | ✗ ADA KEBOCORAN AKTIF

REKOMENDASI:
1. [aksi spesifik jika ada masalah]
```

## Remediation

Jika ditemukan kebocoran atau missing filter:

**JANGAN langsung terapkan filter baru** — perubahan filter BGP bisa memutus koneksi
ke peer jika salah. Selalu:

1. Presentasikan temuan ke operator dengan detail spesifik
2. Draft perintah remediation dan minta konfirmasi
3. Handoff ke `config_agent` (joko) untuk eksekusi dengan approval

Contoh remediation yang mungkin diperlukan:
```
/routing/filter/rule/add chain=bgp-in-<peer> rule="reject" prefix=<prefix-bocor>
/routing/bgp/session/set [find name=<session>] input.filter=<filter-chain>
```

## Catatan

- Audit prefix leak sebaiknya dilakukan setelah setiap onboarding peer baru
- Prefix count yang naik perlahan (tidak mendadak) biasanya normal — prefix internet bertambah
- Koordinasikan dengan NOC IDREN pusat jika leak melibatkan prefix milik node lain


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
| Prefix leak terdeteksi — KRITIS, tindak segera | Serahkan prefix + perintah withdraw/filter | config_agent |
| Perlu laporan insiden | Serahkan kronologi + dampak | document_agent |
| Tidak ada leak | Tidak perlu handoff | END |
