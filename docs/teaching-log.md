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

## 2026-05-16 — Agent hallucination: format template dicetak verbatim

**Apa yang gagal:** Output morning-check berisi teks LARANGAN KERAS FORMAT verbatim dan tabel
dengan nilai placeholder seperti `GW-A | 3 | 0 | — | ✅`. Agent juga berhenti setelah
`list_routers()` tanpa memanggil tool berikutnya.

**Root cause (dua masalah):**
1. **Example contamination** — Format Output section di skill Markdown berisi nilai konkret
   (`GW-A | 3 | 0`). Model memperlakukan ini sebagai data aktual dan mencetaknya verbatim.
2. **Premature loop break** — `_react_loop` break ketika LLM menghasilkan non-tool-call response.
   Setelah `list_routers()`, model membaca format template dan menghasilkan teks output →
   loop berhenti sebelum tool berikutnya dipanggil.

**Perubahan (3 lapis perlindungan):**
1. Ganti semua nilai konkret di format template dengan `[placeholder]` syntax
2. Hapus blok LARANGAN dari dalam `---` separator (pindah ke Aturan Kritis)
3. Tambah gate transisi eksplisit setelah setiap langkah:
   `"→ LANGKAH X SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL [tool]"`
4. Rule 6 di `_SPECIALIST_SYS`: DILARANG pakai data contoh dari skill sebagai output

**Hasil:** Agent memanggil semua tool yang dibutuhkan sebelum menulis output. Format template
tidak lagi bocor ke output.

**Lesson learned:** Format template dengan nilai konkret = jebakan. Selalu gunakan
`[placeholder]` atau `{NAMA_KOLOM}` untuk nilai yang harus diisi dari tool result.

---

## 2026-05-16 — backup-before-write tidak ter-enforce

**Apa yang gagal:** config_agent memanggil `run_command_write` sebelum `backup_router_config`.
Meskipun instruksi di skill menyebutkan urutan yang benar, LLM tidak selalu mengikutinya.

**Root cause:** Urutan tool call diserahkan ke LLM decision — tidak ada enforcement di code.
LLM kadang "mengoptimalkan" dengan langsung ke write tanpa backup.

**Perubahan:** Code-level enforcement di `config_node`:
- `_backed_up_routers: set[str]` per invocation
- `_auto_backup()` inner function yang trigger approval sebelum write pertama ke setiap router
- Jika LLM call backup duluan → ditandai backed up, `_auto_backup` skip
- Jika operator tolak backup → write dibatalkan, ToolMessage berisi "Write dibatalkan"

**Hasil:** Backup selalu terjadi sebelum write pertama, regardless of LLM tool ordering.

**Lesson learned:** Safety invariants yang kritis tidak boleh bergantung pada LLM mengikuti
instruksi. Selalu enforce di code level. LLM untuk reasoning, code untuk safety.

---

## 2026-05-16 — Global conduct rules di file Python kritis

**Apa yang gagal:** Rules format output (simbol status, tabel Markdown, action items) hardcoded
di `_SPECIALIST_SYS` string di `agents/nodes.py`. Untuk update satu rule, harus edit file
Python kritis dan restart.

**Root cause:** Desain awal tidak memisahkan "conduct rules" dari "node logic".

**Perubahan:** Extract ke `skills/pedoman-agent.md`:
- `_load_pedoman()` baca + strip YAML frontmatter di startup
- `_SPECIALIST_SYS` pakai `{pedoman}` placeholder
- Kedua `.format()` call (specialist + config_node) pass `pedoman=_PEDOMAN`

**Hasil:** Ubah perilaku semua agent dengan edit satu Markdown file, restart. `agents/nodes.py`
tidak perlu disentuh untuk perubahan conduct/format.

**Lesson learned:** Pisahkan "apa yang agent lakukan" (logic di nodes.py) dari "bagaimana agent
berperilaku" (conduct di Markdown). Keduanya berubah dengan frekuensi berbeda.

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

---

## 2026-05-09 — Loop supervisor ∞ setelah specialist selesai

**Apa yang gagal:** Request "buatkan top 10 interface dengan trafik tertinggi" menyebabkan
monitor_agent (eko) loop terus-menerus. Trace: eko call get_traffic_all → kembali ke supervisor
→ supervisor `keyword-fallback(monitoragent): empty or unparseable` → eko lagi → repeat.
Agent berjalan 512s+ tanpa selesai.

**Root cause (dua bug terpisah):**

1. **`_make_specialist_node` safety net hilang:** Jika `need_summary` dan forced summary
   menghasilkan empty content (atau exception), `final_msg` tetap sebagai `ToolMessage`.
   State terakhir berisi ToolMessage, bukan AIMessage.

2. **Supervisor early-exit tidak terpicu:** `supervisor_node` cek `isinstance(last, AIMessage)`.
   Jika last message adalah ToolMessage → early-exit tidak jalan → supervisor LLM dipanggil
   → context panjang + reasoning tokens exhausted num_predict → empty JSON → keyword-fallback
   → monitor_agent lagi → loop infinite.

3. **Root cause fungsional:** `get_traffic_all(metric="stats")` output dipotong 200 char per
   router. Untuk query "top 10 interface lintas semua router", data ini tidak cukup untuk
   dianalisis secara akurat oleh LLM.

**Perubahan:**
- `agents/nodes.py` `_make_specialist_node`: tambah safety net setelah forced summary —
  jika `final_msg` masih bukan AIMessage berisi content, ekstrak `ToolMessage` terakhir
  sebagai fallback AIMessage. Memastikan early-exit supervisor SELALU terpicu.
- `agents/nodes.py` `supervisor_node`: tambah loop guard — jika `next_agent == _prev_agent`
  (akan route ke specialist yang sama yang baru selesai), paksa ke END.
- `tools/traffic.py`: tambah tool `get_top_interfaces_all(limit)` — query semua router
  paralel, parse `_parse_iface_stats`, sort global by RX, return tabel top-N.
- `skills/monitoring/network-traffic-analysis.md`: instruksi eksplisit gunakan
  `get_top_interfaces_all` untuk permintaan top-N lintas router.

**Hasil:** Loop cegah oleh dua safety net berlapis. Query top-10 interface sekarang
ditangani oleh satu tool call paralel (bukan 18 sequential calls).

---

## 2026-05-09 — monitor_agent num_predict exhaustion (reason: length)

**Apa yang gagal:** monitor_agent berhenti di tengah health check — Token Utilization panel
menunjukkan `predict: 100.0%`, `done_reason: length`, durasi 96145ms (~96s), 43.9 tps.
43.9 tps × 96s ≈ 4,220 token = persis menabrak batas `num_predict: 4096`.

**Root cause:** qwen3.5:9b menghitung reasoning/thinking tokens dalam `num_predict`. Health
check 17 router menghasilkan banyak token reasoning sebelum output selesai. Dengan `num_predict=4096`,
output terpotong di tengah — response tidak selesai, laporan tidak lengkap.

**Perubahan:** `num_predict` monitor_agent dinaikkan dari 4096 → 8192 di definition file.

**Hasil:** monitor_agent punya ruang 2× lebih besar untuk reasoning + output. Health check
17 router seharusnya tidak lagi terpotong. Trade-off: worst-case memory naik ~100MB VRAM,
masih aman untuk GPU 12GB dengan total beban saat ini.
