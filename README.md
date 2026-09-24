# NetOpsUI — LLMNetOps Console

Web console untuk operasional jaringan berbasis agent AI. NetOpsUI **tidak menjalankan agent**: chat dan tool jaringan dikerjakan oleh salah satu dari dua backend, sedangkan NetOpsUI menyediakan antarmuka serta pengelolaan skill dan profil agent.

| Backend | Keterangan | Alamat default |
|---|---|---|
| **NetOps Agent** | REST API agent jaringan. Repo dan modulnya saat ini masih bernama `palapa-agent` / `palapa` | `127.0.0.1:8100` |
| **Hermes Agent** | Gateway Hermes, platform `api_server` | `127.0.0.1:8642` |

Hanya **satu backend aktif pada satu waktu**, dipilih di **Settings** dan diingat per browser.

## Daftar isi

- [Arsitektur](#arsitektur) · [Fitur](#fitur) · [Manager service](#manager-service-server)
- [Menjalankan / deploy](#menjalankan--deploy)
- [Operasi harian](#operasi-harian) · [Troubleshooting](#troubleshooting) · [Keamanan](#keamanan)
- [Struktur repo](#struktur-repo)

## Arsitektur

```
Browser (SPA vanilla JS)
   │  /backend/netops/*    /backend/hermes/*     /api/*
   ▼
nginx  (container frontend, :3000)
   │  buang header Origin; sisipkan            │
   │  Authorization: Bearer $HERMES_API_KEY    │
   ▼  (khusus Hermes)                          ▼
NetOps Agent :8100        Hermes :8642      manager :8200  (container manager: FastAPI + SQLite)
                                            skill library · profil agent · view config
                                                  │ akses file terbatas
                                                  ▼
                                            ~/.palapa  ·  ~/.hermes
```

- `frontend/js/backends/`: satu adapter per backend dengan kontrak yang sama (lihat komentar di `index.js`). Screen hanya bicara lewat `activeBackend()`.
- `server/`: **manager**, service milik NetOpsUI untuk hal yang tidak punya API di kedua backend.
- Kedua container memakai **host network** agar bisa menjangkau backend yang hanya mendengarkan di `127.0.0.1`. Backend tidak perlu dibuka ke jaringan.
- API key Hermes hanya ada di environment nginx, tidak pernah sampai ke browser.

## Fitur

| Halaman | Isi |
|---|---|
| **Dashboard** | Health backend aktif, model, jumlah thread dan skill, thread terakhir |
| **AI Chat** | Streaming, panel tool activity, stop, riwayat thread. Approval command berisiko hanya di Hermes |
| **Skills** | Library skill di NetOpsUI: buat/edit, import dari disk backend, **publish** ke backend, cabut |
| **Agents** | Profil agent (prompt): dipakai per-chat di Hermes, atau diterapkan ke `SOUL.md` NetOps Agent |
| **Settings** | Pilih backend aktif; tab *File Konfigurasi* menampilkan `config.yaml`, nama variabel `.env`, dan `SOUL.md` |
| Nodes, Reports, Backups, Metrics | **Belum tersedia**: belum ada API-nya di kedua backend |

Perbedaan perilaku antar backend:

- **NetOps Agent**: `/chat` stateless, jadi riwayat chat disimpan di `localStorage` browser dan seluruh history dikirim tiap giliran. Stop hanya memutus stream; proses di server tetap selesai. Tidak ada approval (tool read-only). Persona berasal dari `SOUL.md`.
- **Hermes**: riwayat tersimpan sebagai session di server Hermes. Stop menghentikan run. Command berisiko memunculkan dialog approval (sekali / sesi ini / selalu / tolak). Profil agent aktif dikirim tiap run sebagai `instructions`.

## Manager service (`server/`)

- **Skills**: database SQLite adalah sumber kebenaran. *Publish* menulis `SKILL.md` ke `<NETOPS_AGENT_HOME>/skills/<slug>/` atau `<HERMES_HOME>/skills/netopsui/<slug>/`. Status per backend: Draft, Tersinkron, Perlu publish, Diubah di backend. Publish ditolak jika file tujuan bukan hasil publish NetOpsUI, kecuali dikonfirmasi. Menghapus skill dari library **tidak** menghapus file yang sudah dipublish.
- **Profil agent**: disimpan di SQLite. *Terapkan ke SOUL.md* menimpa persona NetOps Agent dan mencadangkan versi lama ke `data/backups/`.
- **View config**: `config.yaml` ditampilkan dengan nilai rahasia disamarkan (berdasarkan nama key: `key`, `token`, `secret`, `passw`, `credential`, `auth`; referensi `${ENV_VAR}` tetap terlihat). `.env` hanya menampilkan **nama** variabel.

Hak akses container manager sengaja minimal: hanya `skills/` kedua backend dan `SOUL.md` NetOps Agent yang bisa ditulis; `config.yaml`, `.env`, dan `SOUL.md` Hermes read-only; `sessions.db` dan sisanya tidak di-mount.

---

## Menjalankan / deploy

### Prasyarat

| Kebutuhan | Keterangan |
|---|---|
| Docker Engine + Compose v2 | `docker compose version` |
| Host Linux | `network_mode: host` tidak berfungsi di Docker Desktop macOS/Windows |
| Backend berjalan | NetOps Agent dan/atau Hermes, lihat langkah 1 |
| Port kosong | UI `3000`, manager `8200`, NetOps Agent `8100`, Hermes `8642` (semua bisa diubah di `.env`) |

> Di host yang sekarang, port **8000** dipakai container `mikrotik-mcp`, jadi NetOps Agent dijalankan di **8100**.

### 1. Siapkan backend

**NetOps Agent.** API-nya membaca `config.yaml` dari folder tempat ia dijalankan, kecuali `PALAPA_CONFIG_PATH` diatur:

```bash
cd /path/ke/palapa-agent
PALAPA_CONFIG_PATH=$HOME/.palapa/config.yaml \
  uv run uvicorn palapa.gateway.api:app --host 127.0.0.1 --port 8100
```

Untuk permanen, jalankan sebagai service (systemd) supaya otomatis hidup setelah reboot. Kelola sesuai panduan backend tersebut.

**Hermes.** Aktifkan platform `api_server` dengan menambahkan ke `~/.hermes/.env`:

```bash
API_SERVER_KEY=<key-acak-yang-kuat>      # mis. hasil: openssl rand -hex 32
```

lalu restart gateway Hermes. Restart ini memutus sebentar platform lain yang sedang terhubung (mis. Telegram).

Cek backend sebelum lanjut:

```bash
curl -s localhost:8100/health                       # NetOps Agent → {"status":"ok","model":...}
curl -s localhost:8642/health                       # Hermes       → {"status":"ok","platform":"hermes-agent",...}
```

### 2. Konfigurasi NetOpsUI

```bash
git clone <url-repo> NetOpsUI && cd NetOpsUI
git checkout ui
cp .env.example .env
$EDITOR .env
```

Yang **wajib** diperiksa di `.env`:

| Variabel | Isi |
|---|---|
| `HERMES_API_KEY` | Sama persis dengan `API_SERVER_KEY` di `~/.hermes/.env` |
| `NETOPS_AGENT_HOME` | Folder home NetOps Agent (saat ini `/home/<user>/.palapa`) |
| `HERMES_HOME` | Folder home Hermes (`/home/<user>/.hermes`) |
| `HOST_UID` / `HOST_GID` | Hasil `id -u` dan `id -g`, agar file yang ditulis manager dimiliki user Anda |
| `NETOPS_AGENT_URL`, `HERMES_URL` | Ubah hanya jika port backend berbeda dari default |

Pastikan file-file ini **sudah ada** di host, karena file tunggal yang di-mount akan dibuat Docker sebagai *folder* jika tidak ada:
`$NETOPS_AGENT_HOME/{SOUL.md,config.yaml,.env}` dan `$HERMES_HOME/{SOUL.md,config.yaml,.env}`. Folder `data/` sudah ikut di repo (`data/.gitkeep`) dan harus dimiliki user Anda, bukan `root`.

### 3. Build dan jalankan

```bash
docker compose up -d --build
docker compose ps          # kedua service harus "healthy"
```

`frontend` baru start setelah `manager` sehat.

### 4. Verifikasi

```bash
curl -s localhost:3000/api/health                   # manager → {"status":"ok","backends":{"netops":true,"hermes":true}}
curl -s localhost:3000/backend/netops/health        # lewat proxy → health NetOps Agent
curl -s localhost:3000/backend/hermes/health        # lewat proxy → health Hermes
```

Lalu buka `http://<host>:3000`. Header menampilkan backend aktif dengan titik hijau bila terhubung. Pilih backend di **Settings**.

### Mode development (hot reload)

Frontend disajikan langsung dari working tree; cukup reload browser setelah mengubah JS/CSS:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## Operasi harian

| Tugas | Perintah |
|---|---|
| Lihat status | `docker compose ps` |
| Lihat log | `docker compose logs -f manager` · `docker compose logs -f frontend` |
| Restart | `docker compose restart` |
| Stop | `docker compose down` (data di `data/` tetap ada) |
| **Update versi** | `git pull && docker compose up -d --build` |
| Ubah `.env` | edit `.env`, lalu `docker compose up -d` (container dibuat ulang) |
| Setelah ubah kode frontend (tanpa override dev) | `docker compose up -d --build frontend` |

**Update** aman untuk data: database di `data/` dipertahankan, dan perubahan skema/nama yang diperlukan dimigrasi otomatis saat manager start. Pilihan backend dan riwayat chat di browser juga ikut termigrasi.

**Backup.** Yang perlu dicadangkan hanya `data/` (database skill/profil dan cadangan `SOUL.md`) dan `.env`:

```bash
docker compose stop manager
tar czf netopsui-backup-$(date +%F).tgz data .env
docker compose start manager
```

Skill yang sudah dipublish ada di folder skill masing-masing backend dan ikut cadangan backend tersebut.

**Rollback.** `git checkout <commit-atau-tag-sebelumnya> && docker compose up -d --build`. Untuk mengembalikan data, hentikan manager, ganti isi `data/` dari cadangan, lalu start lagi.

## Troubleshooting

| Gejala | Penyebab dan solusi |
|---|---|
| `502 Bad Gateway` di `/backend/netops/…` atau `/backend/hermes/…` | Backend belum berjalan atau port salah. Cek `curl localhost:8100/health` / `:8642/health`. UI tetap jalan; header menampilkan titik merah. |
| Hermes: chat gagal `401`/`403` | `HERMES_API_KEY` di `.env` tidak sama dengan `API_SERVER_KEY`, atau `api_server` belum aktif. Setelah mengubah `.env`, jalankan `docker compose up -d`. |
| `manager` terus restart, log `unable to open database file` | `data/` dimiliki `root` (dibuat Docker karena tidak ada) atau `HOST_UID/GID` salah. `sudo chown -R $(id -u):$(id -g) data`, cek `HOST_UID/GID`. |
| `not a directory` / mount error saat `up` | File yang di-mount belum ada di host dan Docker membuatnya sebagai folder. Hapus folder itu, buat file aslinya, ulangi. |
| `set NETOPS_AGENT_HOME in .env` | Variabel wajib belum diisi di `.env`. |
| Port sudah dipakai | Ubah `UI_PORT` / `MANAGER_PORT` di `.env`. Port 8000 di host ini milik `mikrotik-mcp`. |
| Publish skill ditolak (409) | File tujuan sudah ada dan bukan hasil publish NetOpsUI. Periksa isinya, lalu konfirmasi timpa bila memang diinginkan. |
| Perubahan JS tidak muncul | Tanpa override dev, image harus di-rebuild: `docker compose up -d --build frontend`, lalu hard refresh (Ctrl+Shift+R). |

## Keamanan

- **UI belum punya autentikasi.** Siapa pun yang bisa membuka UI bisa memakai chat, menulis skill ke folder backend, dan menimpa `SOUL.md` NetOps Agent. Untuk akses di luar localhost, pasang lapisan autentikasi di depannya (reverse proxy dengan basic auth/SSO, VPN, atau firewall yang membatasi port `3000`).
- Backend dan manager hanya mendengarkan di `127.0.0.1`; hanya port UI yang terbuka.
- `.env` berisi `HERMES_API_KEY`; jangan di-commit (sudah di `.gitignore`).
- Penyamaran nilai rahasia di view config berdasarkan **nama key**. Rahasia yang disimpan di key bernama lain tidak akan tersamar.

## Struktur repo

```
docker-compose.yml · docker-compose.dev.yml · .env.example · .dockerignore
data/                     database manager + backup SOUL.md (isi tidak di-commit)
frontend/
├── index.html, css/, fonts/, assets/
├── js/
│   ├── app.js, shell.js, state.js, config.js, utils.js, manager.js
│   ├── backends/         common.js · netops.js · hermes.js · index.js
│   └── screens/          dashboard · chat · skills · agents · settings · unavailable
├── nginx.conf.template   proxy ke backend + manager (envsubst saat start)
└── Dockerfile
server/                   manager: main.py · backends.py · db.py · Dockerfile
docs/                     dokumen desain lama (era monolit LangGraph) + mockup Stitch
```

`docs/` masih berisi desain era monolit LangGraph. Yang masih relevan hanya mockup dan `DESIGN.md` di `docs/stitch_llmnetops_enterprise_console/` sebagai acuan visual.
