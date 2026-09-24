# CLAUDE.md — NetOpsUI (LLMNetOps Console)

Repo ini adalah **UI + service manajemen kecil**. Tidak ada logika agent, LLM, atau SSH ke router di sini. Agent dijalankan oleh dua backend yang dipanggil lewat API:

- **NetOps Agent** (repo saat ini masih `palapa-agent`, `/home/llmnetops/palapa-agent`): disebut **NetOps Agent** di seluruh NetOpsUI (UI, id backend `netops`, env `NETOPS_AGENT_*`). Nama `palapa` hanya dipakai saat merujuk ke hal nyata di sisi Palapa: perintah `uvicorn palapa.gateway.api`, `PALAPA_CONFIG_PATH`, folder `~/.palapa`, dan namespace `metadata.palapa` di `SKILL.md`.
- **Hermes** (`~/.hermes/hermes-agent`): gateway platform `api_server`.

Hanya satu backend aktif pada satu waktu (`localStorage['llmnetops-backend']`, dipilih di Settings).

**Scope kerja: hanya repo NetOpsUI.** Jangan mengubah repo palapa-agent, `~/.palapa`, atau `~/.hermes`, dan jangan menjalankan/menghentikan backend tanpa diminta. Pengujian memakai mock dan *salinan* home backend, bukan yang asli. (Pengecualian yang disengaja: fitur Publish skill dan "Terapkan ke SOUL.md" di manager menulis ke folder backend atas aksi operator.)

## Menjalankan

```bash
cp .env.example .env         # isi HERMES_API_KEY, HOST_UID/GID, NETOPS_AGENT_HOME/HERMES_HOME
docker compose up -d --build                                              # produksi
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d      # dev (hot reload)
```

UI di `:3000`, manager di `127.0.0.1:8200`. Backend harus sudah jalan di host: NetOps Agent di `127.0.0.1:8100` (port 8000 dipakai container mikrotik-mcp; API-nya butuh `PALAPA_CONFIG_PATH`), Hermes di `127.0.0.1:8642` (butuh `API_SERVER_KEY` di `~/.hermes/.env`). Detail di README.

## Branch

Pengembangan dilakukan langsung di branch `ui`.

## Arsitektur

```
screens/*.js → backends/index.js activeBackend() → backends/{netops,hermes}.js → /backend/<id>/… → nginx → backend
screens/{skills,agents}.js, settings (tab file) → manager.js → /api/… → nginx → server/ (FastAPI + SQLite) → ~/.palapa, ~/.hermes
```

- **`frontend/js/backends/index.js`**: registry dan **kontrak adapter** (komentar di atas file). Screen tidak boleh `fetch` langsung ke backend.
- **`backends/common.js`**: `http()`, `readSSE()` (mendukung `event:` dan multi-line `data:`), `toDate()`, `contentText()`.
- **`backends/netops.js`**: `/chat` stateless, jadi thread + pesan disimpan di `localStorage['llmnetops-netops-threads-v1']` (key lama `…palapa…` dan id backend `palapa` dimigrasi otomatis) dan seluruh history dikirim tiap giliran. Stop = `AbortController` (run di server tidak berhenti). Tidak ada approval.
- **`backends/hermes.js`**: thread = Hermes session. Giliran chat memakai **`POST /v1/runs` + `GET /v1/runs/{id}/events`**, bukan `/api/sessions/{id}/chat/stream`, karena hanya runs yang mengirim `approval.request` dan menerima `/approval` dan `/stop`. Profil agent aktif dikirim sebagai `instructions`.
- **`frontend/nginx.conf.template`**: proxy `/backend/netops/`, `/backend/hermes/`, `/api/` (manager). Menyisipkan `Authorization: Bearer $HERMES_API_KEY` dan **mengosongkan `Origin`** (Hermes menolak origin di luar `API_SERVER_CORS_ORIGINS`).
- **`server/`** (manager): `backends.py` (akses filesystem terbatas, render/parse `SKILL.md`, masking config), `db.py` (SQLite: `skills`, `skill_publications`, `profiles`; baris `backend='palapa'` dimigrasi ke `netops` saat start), `main.py` (API). Skill = folder `<slug>/SKILL.md` dengan frontmatter YAML di kedua backend; Hermes menaruh skill NetOpsUI di `skills/netopsui/`.

### Event ternormalisasi (dikonsumsi `screens/chat.js`)

`delta` · `tool_start` · `tool_end` · `note` · `thinking` · `approval` · `error` · `stopped`. Backend baru = adapter yang memetakan event-nya ke daftar ini, lalu didaftarkan di `BACKENDS`.

### Screen "belum tersedia"

`NAV_ITEMS[].unavailable = true` di `config.js` → `screens/unavailable.js`. Saat ini: Nodes, Reports, Backups, Metrics. Aktifkan kembali dengan menghapus flag, menambah screen, dan method adapter/manager setelah datanya ada.

## Aturan

- **Jangan simpan API key/credential di JS.** Kredensial disisipkan nginx dari env container. Manager tidak pernah mengembalikan nilai `.env`; `config.yaml` selalu dimasking.
- Di nginx, `proxy_set_header` **tidak diwarisi** ke `location` yang punya `proxy_set_header` sendiri. Setiap location mengulang header lengkap.
- Manager: slug divalidasi `^[a-z0-9][a-z0-9-]{0,63}$` dan path skill dicek tetap di dalam folder skills (anti path traversal). `SOUL.md` ditulis *in place* (bisa berupa bind mount satu file yang tidak bisa di-rename atomik).
- Publish skill tidak menimpa file yang bukan hasil publish NetOpsUI tanpa `force`. Menghapus skill di library tidak menghapus file yang sudah dipublish.
- File tunggal yang di-mount di compose harus sudah ada di host, dan `data/` harus ada (`data/.gitkeep`) agar tidak dibuat `root` oleh Docker.
- **Pengujian harus memakai `DATA_DIR` terpisah** (dan salinan home backend). `./data` berisi data asli operator; stack uji yang memakai `./data` yang sama akan bercampur dengannya.
- **Jangan mematikan proses dengan `pkill -f`/`pgrep -f` berdasarkan nama** (mis. `uvicorn main:app`): proses di dalam container terlihat di host dan ikut terbunuh. Gunakan PID atau port uji yang unik.
- Tidak ada build step: ES modules langsung, Tailwind via CDN (config di `index.html`), markdown renderer sendiri di `utils.js` (escape-first). `localStorage` bisa kosong/throw, selalu `try/catch`.
- **UI belum punya autentikasi.**

## Bahasa

- **Kode:** Bahasa Inggris (nama variabel, komentar). **Teks UI untuk operator:** Bahasa Indonesia.

## File Tidak Di-commit

```
.env      # HERMES_API_KEY, URL backend, HOST_UID/GID
data/*    # database manager + backup SOUL.md (kecuali data/.gitkeep); lokasi bisa diganti via DATA_DIR
```

## Dokumentasi

`docs/` berisi dokumen desain era monolit LangGraph (tidak lagi mencerminkan kode) dan mockup Stitch di `docs/stitch_llmnetops_enterprise_console/`, yang masih menjadi acuan visual.

## Agent skills

### Issue tracker

Issues dikelola sebagai file Markdown di `.scratch/`. Lihat `docs/agents/issue-tracker.md`.

### Triage labels

Label dalam Bahasa Indonesia: perlu-triage, perlu-info, siap-agent, siap-manusia, tidak-dikerjakan. Lihat `docs/agents/triage-labels.md`.

### Domain docs

Single-context: satu `CONTEXT.md` di root + `docs/adr/`. Lihat `docs/agents/domain.md`.
