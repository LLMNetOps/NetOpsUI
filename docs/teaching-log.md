# Teaching Log — llmnetops

Log per sesi: apa yang gagal, root cause, perubahan yang dilakukan, dan hasilnya.
Tujuan: institutional memory agar alasan di balik setiap keputusan tidak hilang.

Format:
```
## [YYYY-MM-DD] — [topik]
**Apa yang gagal:** ...
**Root cause:** ...
**Perubahan:** ...
**Hasil:** ...
```

---

## 2026-05 — Migrasi model gemma4:e4b → qwen3.5:9b

**Apa yang gagal:** Supervisor menghasilkan response kosong, JSON parse error terus-menerus.
`done_reason: 'length'`, `eval_count == num_predict`, `content: ''`.

**Root cause:** gemma4:e4b adalah thinking model — token reasoning dihitung dalam `num_predict`.
Dengan `num_predict=256` (default lama), semua token habis untuk thinking sebelum menghasilkan
output JSON. Model tidak menghasilkan konten sama sekali.

**Perubahan:** `num_predict` supervisor dinaikkan ke 2048 di definition file.

**Hasil:** Supervisor mulai menghasilkan JSON routing yang valid. Setelah itu ganti model ke
qwen3.5:9b (6.1 GB VRAM vs gemma4:e4b 8.9 GB) karena lebih efisien dan lebih capable.

---

## 2026-05 — qwen3.5:9b tokenizer lebih verbose

**Apa yang gagal:** Context overflow — prompt yang sama di qwen3.5:9b menghasilkan lebih banyak
token: 1791 token vs 817 token di gemma4.

**Root cause:** Tokenizer qwen3.5:9b lebih verbose untuk teks Indonesia. Dengan `num_ctx=4096`
lama, supervisor kehabisan context saat memproses percakapan panjang.

**Perubahan:** `num_ctx` supervisor dinaikkan dari 4096 → 8192 di definition file.

**Hasil:** Supervisor bisa handle percakapan lebih panjang tanpa truncation.

---

## 2026-05 — monitor_agent gagal cek 17 router (max_iters)

**Apa yang gagal:** Request "cek status semua router" berhenti di tengah jalan.
Hanya 11-12 router yang dicek dari 17 total.

**Root cause:** `max_iters=12` di `_react_loop`. Setiap router = 1 LLM iteration untuk
memanggil `check_reachability`. Campus punya 17 router → butuh minimal 17 iterasi.

**Perubahan:** `max_iters` dinaikkan dari 12 → 20 di `_react_loop` di `nodes.py`.

**Hasil:** monitor_agent berhasil iterasi semua 17 router. Trade-off: waktu eksekusi
lebih lama (~270 detik untuk health check lengkap).

---

## 2026-05 — Supervisor loop tidak berhenti (forced summary)

**Apa yang gagal:** Setelah specialist selesai, supervisor terus loop tanpa menghasilkan
response akhir. Graph berjalan sampai recursion limit.

**Root cause:** Dua kondisi menyebabkan ini:
1. Specialist return `AIMessage` kosong (thinking-only, content='')
2. Specialist return `ToolMessage` karena `max_iters` tercapai
Keduanya tidak dikenali supervisor sebagai "specialist sudah selesai".

**Perubahan:** `_make_specialist_node` ditambah logika `need_summary`: jika last message
bukan AIMessage dengan content, force plain LLM call untuk menghasilkan summary.

**Hasil:** Supervisor selalu mendapatkan AIMessage dengan content dari specialist.
Loop berhenti secara normal.

---

## 2026-05 — Supervisor tidak membalas sapaan (has_ai_reply bug)

**Apa yang gagal:** Setelah percakapan panjang, supervisor tidak membalas pesan pendek
seperti "hai" atau "terima kasih". Langsung routing ke specialist.

**Root cause:** `has_ai_reply` mengecek seluruh `recent_window` untuk AIMessage.
Jika ada AIMessage dari pesan sebelumnya, supervisor mengira sudah membalas dan skip.

**Perubahan:** `has_ai_reply` diubah untuk hanya mengecek messages **setelah**
`last_human_idx` (posisi HumanMessage terakhir di state).

**Hasil:** Supervisor membalas sapaan dan pesan pendek dengan benar, tanpa langsung
routing ke specialist yang tidak perlu.

---

## 2026-05 — Keyword fallback routing

**Apa yang gagal:** Sesekali supervisor gagal parse JSON routing decision, menyebabkan
agent berhenti tanpa tindakan.

**Root cause:** JSON parse error dari LLM output yang tidak valid (trailing whitespace,
kutip tidak seimbang, thinking tag bocor ke content).

**Perubahan:** Tambah `_keyword_route()` di `nodes.py` — fallback yang menganalisis
kata kunci dari pesan user terakhir:
- monitor/status/cek router → monitor_agent
- config/backup → config_agent
- keamanan/security → security_agent
- diagnosa/error/masalah → diagnose_agent
- laporan/dokumen → document_agent

**Hasil:** Agent tidak berhenti total saat JSON parse gagal. Routing tetap terjadi
meskipun kurang presisi.

---

## 2026-05 — Sistem evaluasi scenario (eval.py)

**Konteks:** Tidak ada cara mengukur apakah perubahan skill/prompt memperbaiki atau
merusak perilaku yang sudah benar.

**Yang dibangun:**
- `tests/scenarios/*.yaml` — 5 skenario representatif (BGP/OSPF report, health check,
  brute force detect, DHCP exhaustion, interface flapping)
- `tests/mocks/fixtures.py` — mock data realistis per tool, tidak butuh koneksi router
- `tests/eval.py` — evaluator yang patch TOOL_MAP dengan mock, jalankan agent,
  verifikasi expected_agents, expected_tools, dan acceptance_criteria

**Temuan dari run pertama (health-check):**
- Framework bekerja: routing ke monitor_agent benar, list_routers + check_reachability dipanggil ✓
- `output_contains_any` terlalu strict — AI merangkum dalam bahasa Indonesia, tidak selalu
  menggunakan kata "reachable" verbatim
- Fix: tambah `trace_contains_any` yang memeriksa seluruh event trace termasuk tool results

**Hasil:** 4/5 checks pass pada run pertama. Criterion diperbaiki untuk run berikutnya.

**Cara pakai:**
```bash
python tests/eval.py              # semua scenarios
python tests/eval.py health-check # satu scenario
python tests/eval.py --lab        # pakai router nyata (containerlab)
```

---

## Catatan Umum — Pola yang Sering Muncul

### Model kecil vs instruksi ambigu
qwen3.5:9b bekerja jauh lebih baik dengan instruksi prosedural eksplisit daripada
instruksi deskriptif. "Cek interface stats lalu identifikasi error rate > 0" menghasilkan
tindakan yang benar. "Analisis kondisi interface" sering tidak menghasilkan tool call.

### Sequential tool calls = bottleneck
17 router × 1 LLM call per router = 17+ iterasi untuk health check.
Ini adalah trade-off desain: simplicity vs speed. Solusi batch (check_reachability_all)
dipertimbangkan tapi belum diimplementasi karena menambah kompleksitas tool interface.

---

## 2026-05-09 — Pending review gate untuk skill baru

**Konteks:** Skill yang digenerate qwen3.5:9b via write_skill langsung masuk production.
Tidak ada kesempatan untuk review kualitas, syntax RouterOS, atau kepatuhan terhadap
infrastruktur kampus UB yang spesifik.

**Arsitektur yang diimplementasikan — Two-tier intelligence:**
```
qwen3.5:9b (runtime)     →  kecepatan + privasi + operasional harian
Claude (development)     →  kualitas + kedalaman + knowledge engineering
```

**Perubahan:**
- `write_skill` sekarang simpan ke `skills/.pending/{domain}/{name}.md`, bukan langsung live
- `tests/review.py` — CLI untuk list, show (+ checklist 9 item), approve, reject
- `skill-authoring.md` diupdate: agent instruksi untuk inform operator tentang pending status
- Workflow: agent buat skill → pending → Claude review di Claude Code → approve → live

**Nilai review gate:**
1. Claude bisa cek syntax RouterOS (qwen3.5:9b mungkin generate command ROS v6 untuk router v7)
2. Claude bisa cek apakah tools yang dipakai ada di TOOL_MAP
3. Claude bisa cek apakah prosedur masuk akal untuk infrastruktur kampus UB
4. Human-in-the-loop tetap terjaga untuk perubahan yang mempengaruhi behavior sistem

**Batasan:** Claude tidak membaca data produksi (log traffic, IP aktif) — hanya review
struktur dan logika skill. Review tetap memerlukan domain knowledge dari Alan untuk
hal-hal spesifik kampus.

### Skill injection timing
Supervisor menginject skill context ke specialist sebelum specialist jalan.
Jika skill terlalu panjang, ia memenuhi context window dan mendorong keluar riwayat
tool calls sebelumnya. Panjang ideal skill: 60-100 baris efektif (setelah frontmatter).

---

## 2026-05-09 — Meta-capability: write_skill via agent

**Apa yang gagal:** document_agent bertanya-tanya ("Mari saya tanyakan beberapa hal...") alih-alih
langsung membuat skill saat diminta "buat skill baru untuk diagnosa MTU mismatch".

**Root cause:** Langkah 3 di `skill-authoring.md` ("Kumpulkan Informasi dari Operator") terlalu
mudah terpicu. qwen3.5:9b memutuskan perlu info tambahan padahal topik "MTU mismatch" sudah jelas.

**Perubahan:** Rewrite Langkah 2/3 di `skill-authoring.md`:
- Tambah daftar topik teknis yang cukup jelas untuk langsung dibuat tanpa bertanya
- Default behavior: langsung buat, tanya hanya jika permintaan benar-benar ambigu
- Fix penomoran langkah yang loncat (1→3→4→5→6→7 → 1→2→3→4→5→6→7)

**Hasil:** document_agent langsung memanggil write_skill tanpa bertanya. 4/4 checks pass, 76.7s.

---

## 2026-05-09 — Supervisor loop setelah skill-authoring

**Apa yang gagal:** Setelah document_agent berhasil menulis skill, supervisor loop 9x ke
diagnose_agent. Trace: JSON parse error → keyword-fallback "diagnosa" → diagnose_agent → repeat.

**Root cause:** Override "force END setelah document_agent" di nodes.py punya kondisi
`_wants_file`. Untuk request "buat skill baru", `_wants_file = False` (keyword tidak cocok)
→ override tidak terpicu → supervisor terus loop.

**Perubahan:** Hapus kondisi `_wants_file` dari override line 327 di `nodes.py`:
```python
# Sebelum:
if next_agent != "END" and _prev_agent == "document_agent" and _wants_file:
# Sesudah:
if next_agent != "END" and _prev_agent == "document_agent":
```
document_agent selalu terminal (`handoff_to: []`), jadi setelah selesai selalu END — apapun yang ditulis.

**Hasil:** Loop hilang. Waktu eksekusi turun dari 249.7s → 76.7s. Scenario skill-authoring PASS.
