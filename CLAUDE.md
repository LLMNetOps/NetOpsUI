# CLAUDE.md — llmnetops

Platform operasional jaringan kampus berbasis LangGraph multi-agent. Agent SSH ke router MikroTik (RouterOS v6/v7), menganalisis kondisi jaringan, dan mengeksekusi perubahan dengan approval operator.

## Cara Menjalankan

```bash
source .venv/bin/activate
python tui.py          # TUI ncurses (production)
python server.py       # Web server (FastAPI) — http://localhost:8000
# python tui_textual.py  # TUI Textual (experimental)
```

Membutuhkan `config.yaml` (tidak di-commit) dan `.env` dengan `OLLAMA_BASE_URL` + `OLLAMA_MODEL`.

## Branch

| Branch | Deskripsi |
|--------|-----------|
| `main` | DHCP monitoring UTBK (original, jangan diubah) |
| `netops` | Fondasi multi-agent platform |
| `refactor_agent_skill_tool` | Branch aktif pengembangan |

PR selalu ke `main` dari branch aktif.

---

## Arsitektur Singkat

```
tui.py  →  agent.py (public API)  →  agents/nodes.py  →  tools/*.py  →  Router SSH
                                         ↑
                               agents/definitions/*.md   skills/**/*.md
```

- **`agent.py`** — hanya public API: `create_agent()`, `stream_agent_response()`, `resume_after_approval()`. Zero LLM logic.
- **`agents/nodes.py`** — semua node LangGraph: `supervisor_node`, `_make_specialist_node()` factory, `config_node`.
- **`agents/loader.py`** — baca `agents/definitions/*.md`, parse frontmatter YAML jadi `AgentDefinition`.
- **`agents/tools.py`** — `TOOL_MAP: dict[str, tool]` — registry semua tools per domain.
- **`tools/*.py`** — 31+ atomic `@tool` functions, semua SSH ke MikroTik.
- **`skills/library.py`** — `SkillLibrary` dengan hot reload via `watchfiles`.
- **`skills/**/*.md`** — prosedur kerja agent; ditambah tanpa coding Python.
- **`tui.py`** — UI only, consume `agent.py` public API, zero LLM logic.

---

## Agent Definitions (`agents/definitions/*.md`)

Setiap file Markdown mendefinisikan satu specialist agent. Frontmatter YAML:

```yaml
---
name: monitor_agent      # snake_case, cocok dengan nama node di graph
alias: eko               # nama tampilan di TUI
description: >           # dipakai supervisor untuk routing decision
  Satu kalimat fungsi agent
model: qwen3.5:9b
num_ctx: 32768           # KV cache VRAM ~3.5 GB per agent — aman karena sekuensial
num_predict: 16384       # thinking model: token reasoning ikut dihitung
context_window: 20       # jumlah pesan terakhir yang dibawa ke LLM
timeout: 600
ollama_host: ""          # opsional; override OLLAMA_BASE_URL untuk multi-mesin
tools:
  - list_routers         # harus ada di TOOL_MAP di agents/tools.py
  - check_reachability
skills:
  - network-health-check # harus ada di skills/**/*.md
handoff_to:
  - document_agent       # agent yang boleh di-route berikutnya
approval_required_tools: # khusus config_agent — tools yang picu interrupt()
  - backup_router_config
  - run_command_write
---
Isi system prompt agent dalam Bahasa Indonesia...
```

**Aturan:** Jangan tambahkan instruksi "tunggu konfirmasi dari operator" atau "satu perubahan sekaligus" di system prompt — ini menyebabkan agent berhenti setelah approval pertama.

---

## Skill Format (`skills/**/*.md`)

```yaml
---
name: nama-skill         # kebab-case, cocok dengan referensi di agent definition
domain: monitoring       # direktori domain: monitoring/routing/config/security/dhcp/...
triggers:
  - kata kunci query yang relevan
tools:
  - get_interface_stats  # informational — tidak enforce di runtime
approval_required: false
enabled: true
---

Konten prosedur dalam Bahasa Indonesia...
```

Skill baru langsung aktif tanpa restart (hot reload). Tempatkan di subdirektori domain yang sesuai.

---

## Tool Conventions (`tools/*.py`)

**Naming:**
- `get_*` — read, return data
- `run_command` — read-only SSH command (blocklist kata destruktif)
- `run_command_write` — write SSH command (butuh approval, blocklist `format`/`factory-reset`)
- `audit_*` — multi-router parallel check
- `check_*` — boolean/status check
- `list_*` — daftar item
- `backup_*` — operasi backup (butuh approval)

**Jangan tambahkan truncation limit baru.** Limit yang ada sudah sengaja diperbesar atau dihapus karena menyebabkan agent kehilangan konteks. Jika output terlalu besar, perbaiki di sisi query MikroTik, bukan potong hasilnya.

**Tools yang butuh approval operator** (via `interrupt()` di `config_node`):
- `backup_router_config`
- `run_command_write`

---

## Pola Penting di `agents/nodes.py`

### Safety Net (jamin AIMessage selalu ada)

Setelah forced summary, jika `final_msg` bukan `AIMessage` berisi konten:
```python
# Ambil ToolMessage dengan konten terpanjang sebagai fallback
best = max(tool_msgs, key=lambda m: len(m.content or ""))
final_msg = AIMessage(content=f"Hasil:\n{best.content}")
```
**Jangan hapus** — mencegah supervisor loop tak terbatas.

### Loop Guard (di `supervisor_node`)

```python
if next_agent == _prev_agent and _prev_agent in valid_agent_names:
    next_agent = "END"
```
**Jangan hapus** — mencegah supervisor re-route ke agent yang baru saja selesai.

### Approval Chain (di `config_node`)

`config_node` menggunakan `interrupt()` untuk setiap tool di `_APPROVAL_REQUIRED_TOOLS`. `resume_after_approval()` di `agent.py` menggunakan `graph.stream()` (bukan `graph.invoke()`) agar interrupt berikutnya tetap sampai ke TUI.

### Rule 6 di `_SPECIALIST_SYS`

```
Setelah menerima hasil tool, jika masih ada tugas berikutnya, LANGSUNG panggil
tool berikutnya tanpa menulis teks konfirmasi, ringkasan, atau 'Lanjut ke langkah X'.
```
**Jangan hapus** — mencegah agent berhenti di tengah sequence write operations.

---

## State Graph

```python
class NetworkOpsState(TypedDict):
    messages:     Annotated[list, add_messages]  # pesan LangGraph (append-only)
    next_agent:   str    # target routing dari supervisor
    active_agent: str    # agent yang sedang berjalan
    agent_log:    list   # AgentLogEntry — dikonsumsi TUI untuk Activity screen
    reasoning:    str    # debug reasoning supervisor
    skill_name:   str    # skill yang diinjeksi ke specialist
```

`agent_log` adalah append-only list yang di-yield ke TUI sebagai events: `routing`, `tool_call`, `tool_result`, `ai`, `approval`.

---

## TUI Public API (`agent.py`)

```python
graph, config = create_agent()

# Stream query baru
for event_type, content in stream_agent_response(graph, config, "query user"):
    # event_type: "routing" | "tool_call" | "tool_result" | "ai" | "approval_required" | "error"
    ...

# Resume setelah approval (gunakan ini, bukan graph.invoke)
for event_type, content in resume_after_approval(graph, config, "approved"):
    ...
```

---

## Bahasa

- **Kode Python:** Bahasa Inggris (nama variabel, komentar teknis, docstring)
- **System prompt agent & skill:** Bahasa Indonesia
- **Log output ke operator:** Bahasa Indonesia
- **Dokumen di `docs/`:** campuran (sebagian Inggris, sebagian Indonesia)

---

## File Kritis — Jangan Diubah Tanpa Hati-hati

| File | Alasan |
|------|--------|
| `agents/nodes.py` | Safety net + loop guard; perubahan bisa menyebabkan infinite loop |
| `agent.py` | Public API contract dengan tui.py; `resume_after_approval` harus tetap streaming |
| `tools/config_read.py` | `_BLOCKED_KEYWORDS` — daftar blocklist read-only; jangan relaksasi |
| `tools/config_write.py` | `_BLOCKED_DESTRUCTIVE` — jangan hapus `factory-reset`, `format` |
| `agents/tools.py` | `TOOL_MAP` — tool harus terdaftar di sini agar bisa dipakai agent |

---

## File Tidak Di-commit (gitignored)

```
config.yaml      # kredensial SSH + daftar router
.env             # OLLAMA_BASE_URL, OLLAMA_MODEL
backups/         # hasil backup config router
laporan/         # laporan yang digenerate agent
output/          # output lain
```

---

## Dokumentasi

| Dokumen | Isi |
|---------|-----|
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | 8-phase plan; Phase 8 = TUI Textual (belum dimulai) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Desain sistem lengkap |
| [docs/SKILL_AUTHORING_GUIDE.md](docs/SKILL_AUTHORING_GUIDE.md) | Panduan menulis skill baru |
| [laporan/rekap-pengembangan_20260509.md](laporan/rekap-pengembangan_20260509.md) | Rekap pekerjaan 9 Mei 2026 |

---

## Agent skills

### Issue tracker

Issues dikelola sebagai file Markdown di `.scratch/`. Lihat `docs/agents/issue-tracker.md`.

### Triage labels

Label dalam Bahasa Indonesia: perlu-triage, perlu-info, siap-agent, siap-manusia, tidak-dikerjakan. Lihat `docs/agents/triage-labels.md`.

### Domain docs

Single-context — satu `CONTEXT.md` di root + `docs/adr/`. Lihat `docs/agents/domain.md`.
