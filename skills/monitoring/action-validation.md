---
name: action-validation
domain: monitoring
triggers:
  - validasi action items
  - cek dulu sebelum eksekusi
  - konfirmasi masalah
  - verifikasi temuan
  - wati cek
  - validasi dulu
tools:
  - check_reachability
  - check_ssh_access
  - get_bgp_sessions
  - get_system_info
  - get_router_log
  - get_interface_stats
  - get_ospf_neighbors
  - get_routing_full
  - run_command
  - get_current_time
approval_required: false
enabled: true
---

# Action Validation — Verifikasi Action Items Sebelum Eksekusi

## Konteks

Skill ini digunakan oleh `validasi_agent` (Wati) untuk memvalidasi action items 🚨 SEGERA
yang dihasilkan oleh monitor_agent, diagnose_agent, atau security_agent.

Tujuan: konfirmasi masalah masih ada (temporal validation) dan rekomendasi teknis benar
(epistemic validation) sebelum config_agent atau diagnose_agent mengeksekusi tindakan.

## Prosedur

### Langkah 1: Baca Action Items dari Context

Cari semua item berlabel `🚨 **SEGERA**` dari output agent sebelumnya dalam context percakapan.
Daftar setiap item dengan komponen:
- Router yang terdampak
- Masalah yang dilaporkan (BGP down, unreachable, CPU tinggi, dll.)
- Peer/interface/resource yang spesifik

**Jika tidak ditemukan item 🚨 SEGERA dalam context:** tulis satu baris `✅ Tidak ada action items yang perlu divalidasi.` diikuti `→ tidak perlu tindakan`, lalu BERHENTI.

**→ LANGKAH 1 SELESAI. JANGAN TULIS APAPUN. LANGSUNG mulai verifikasi per item.**

### Langkah 2: Verifikasi Temporal — Masalah Masih Ada?

Untuk setiap item SEGERA, jalankan tool yang relevan:

| Tipe masalah | Tool yang digunakan |
|-------------|---------------------|
| Router unreachable | `check_reachability(router_name)` lalu `check_ssh_access(router_name)` |
| BGP session down | `get_bgp_sessions(router_name)` |
| CPU/memory tinggi | `get_system_info(router_name)` |
| Interface error/flap | `get_interface_stats(router_name)` |
| OSPF neighbor down | `get_ospf_neighbors(router_name)` |
| Log anomali | `get_router_log(router_name, lines=30)` |

Untuk router unreachable: jika `check_reachability` PASS tapi `check_ssh_access` FAIL → masalah SSH/manajemen, bukan router down. Bedakan di verdict.

Bandingkan hasil tool saat ini dengan klaim agent sebelumnya:
- Masalah masih ada → KONFIRMASI
- Masalah sudah hilang sendiri → RESOLVED
- Tidak bisa diverifikasi (SSH error, timeout) → TIDAK DAPAT DIKONFIRMASI

**Jika SEMUA item RESOLVED setelah Langkah 2: LANGSUNG tulis verdict — SKIP Langkah 3.**

**→ LANGKAH 2 SELESAI. JANGAN TULIS APAPUN. LANGSUNG lanjut ke assessment dampak (jika ada KONFIRMASI).**

### Langkah 3: Assessment Dampak (Hanya untuk KONFIRMASI)

Untuk item yang KONFIRMASI, tentukan:
- **Apakah ini primary atau backup?** (backup session DOWN saat primary UP = wajar, tidak perlu tindakan)
- **Berapa lama masalah sudah terjadi?** (dari `last-stopped` atau uptime)
- **Apakah ada failover/redundansi aktif?** (jika ya, dampak minimal)
- **Apakah perlu reset/restart atau investigasi lebih dalam?**

Jika root cause jelas (hold timer expired, auth error, link flap) → config_agent.
Jika root cause tidak jelas atau kompleks → diagnose_agent.

**→ LANGKAH 3 SELESAI. JANGAN TULIS APAPUN. LANGSUNG tulis verdict.**

## Output yang Diharapkan

INSTRUKSI: Tulis output ini HANYA setelah Langkah 1–3 selesai.

---

**VERDICT VALIDASI — [hasil get_current_time()]**

*(Narasi singkat: berapa item yang divalidasi, berapa KONFIRMASI vs RESOLVED)*

## Hasil Verifikasi

| Item | Router | Masalah | Verdict | Alasan |
|------|--------|---------|---------|--------|
| [nama item dari context] | [nama router] | [masalah spesifik] | 🚨 KONFIRMASI / ✅ RESOLVED / ❓ TIDAK DAPAT DIKONFIRMASI | [alasan singkat dari tool result] |

*(Narasi wajib: jelaskan kondisi jaringan saat ini berdasarkan verifikasi — apa yang masih bermasalah, apa yang sudah recover, apa yang perlu tindakan segera. 2–3 kalimat.)*

## Rekomendasi Tindakan

*(Hanya untuk item KONFIRMASI — spesifik, berdasarkan tool result, bukan asumsi)*

1. [Tindakan konkret untuk item yang KONFIRMASI] — router, perintah, atau langkah spesifik

*(Tulis "Tidak ada tindakan yang diperlukan." jika semua item RESOLVED)*

---

*(Tulis TEPAT SATU dari tiga kalimat berikut sebagai baris terakhir output:)*

`→ delegasikan ke config_agent` ATAU `→ delegasikan ke diagnose_agent` ATAU `→ tidak perlu tindakan`

## Aturan Verdict

- **KONFIRMASI** → masalah terbukti masih ada dari tool result aktual
- **RESOLVED** → masalah sudah hilang sendiri, tidak perlu tindakan
- **TIDAK DAPAT DIKONFIRMASI** → tool gagal (SSH timeout, error) — perlakukan sebagai KONFIRMASI
  dengan catatan bahwa verifikasi tidak berhasil; delegasikan ke diagnose_agent untuk investigasi manual

## Catatan

- Backup session DOWN saat primary UP → bukan masalah, tulis RESOLVED
- Jika SEMUA item RESOLVED → tulis `→ tidak perlu tindakan`
- Jika ada KONFIRMASI yang butuh perubahan config (restart session, blokir IP) → `→ delegasikan ke config_agent`
- Jika ada KONFIRMASI yang root cause-nya tidak jelas → `→ delegasikan ke diagnose_agent`
- Jika ada dua tipe sekaligus (config + diagnosa) → `→ delegasikan ke config_agent` (eksekusi lebih mendesak daripada investigasi)


## Validasi Mandiri

Sebelum lapor, pastikan:
- [ ] Setiap item SEGERA sudah diverifikasi dengan tool (bukan asumsi)
- [ ] Verdict didasarkan pada tool result aktual, bukan output agent sebelumnya
- [ ] Baris terakhir adalah tepat satu dari tiga delegation string yang diizinkan

## Handoff

| Kondisi | Aksi | Agent Tujuan |
|---------|------|--------------|
| Ada KONFIRMASI butuh config change | `→ delegasikan ke config_agent` | config_agent |
| Ada KONFIRMASI butuh investigasi dalam | `→ delegasikan ke diagnose_agent` | diagnose_agent |
| Semua RESOLVED atau tidak perlu tindakan | `→ tidak perlu tindakan` | END |

## Contoh Output

**Skenario:** monitor_agent melaporkan BGP session GATE-IDREN-UNESA ke peer 10.20.30.1 down.

---

**VERDICT VALIDASI — 16 Mei 2026, 09:14 WIB**

Ditemukan 1 action item SEGERA. Hasil verifikasi: 1 KONFIRMASI.

## Hasil Verifikasi

| Item | Router | Masalah | Verdict | Alasan |
|------|--------|---------|---------|--------|
| BGP session down | GATE-IDREN-UNESA | Session ke peer 10.20.30.1 state=idle, last-stopped 2j lalu | 🚨 KONFIRMASI | get_bgp_sessions menunjukkan session masih idle, hold-timer expired |

Session BGP ke peer 10.20.30.1 terkonfirmasi masih down dengan state `idle` — bukan flap sementara. Session primary (bukan backup), sudah idle selama 2 jam tanpa recovery otomatis. Root cause hold-timer expired menunjukkan link masih ada tapi keepalive gagal.

## Rekomendasi Tindakan

1. GATE-IDREN-UNESA: reset BGP session ke peer 10.20.30.1 — `/routing/bgp/session/reset`

---

→ delegasikan ke config_agent
