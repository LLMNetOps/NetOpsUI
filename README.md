<p align="center">
  <img src="frontend/assets/llmnetops-logo-with-mascot.png" alt="LLMNetOps" width="640">
</p>

# NetOpsUI — LLMNetOps Console

NetOpsUI adalah konsol web untuk operasional jaringan dengan bantuan agent AI. NetOpsUI **tidak menjalankan agent sendiri**. Percakapan dan eksekusi tool jaringan ditangani oleh salah satu dari dua backend berikut, sedangkan NetOpsUI menyediakan antarmuka web serta layanan manager untuk mengelola thread, skill, dan konfigurasi.

| Backend | Keterangan | Alamat bawaan |
|---|---|---|
| **NetOps Agent** | Agent jaringan dengan REST API (repositori `palapa-agent`) | `127.0.0.1:8100` |
| **Hermes** | Gateway Hermes dengan platform `api_server` | `127.0.0.1:8642` |

Hanya satu backend yang aktif pada satu waktu, dan backend aktif dipilih di **Settings**.

## Fitur

- **Dashboard**: ringkasan status backend, model yang dipakai, jumlah skill, dan thread terbaru. Pada NetOps Agent, dashboard juga menampilkan daftar perangkat dan aktivitas agent. Pada Hermes, dashboard menampilkan pengecekan berkala (cron job).
- **AI Chat**: percakapan dengan agent, dilengkapi panel aktivitas tool, konsol proses, dan riwayat thread. Thread disimpan di server sehingga dapat diakses oleh semua operator. Jawaban agent tetap tersimpan meskipun halaman dimuat ulang atau ditutup.
- **Nodes**: pengelolaan perangkat jaringan pada NetOps Agent, meliputi melihat daftar, menambah, mengubah, dan menghapus perangkat.
- **Skills**: pengelolaan pustaka skill di NetOpsUI dan publikasi skill ke backend.
- **Settings**: pemilihan backend, pengelolaan LLM provider, tampilan file konfigurasi backend, dan penggantian password.

## Tampilan

Halaman login:

![Halaman login](frontend/assets/login-page.png)

Dashboard setelah login:

![Dashboard](frontend/assets/dashboard-page.png)

## Instalasi

### Prasyarat

- Docker Engine dan Docker Compose v2. Periksa dengan `docker compose version`.
- Host **Linux**. Container memakai `network_mode: host`, sehingga tidak dapat dijalankan di Docker Desktop untuk macOS maupun Windows.
- Minimal satu backend (NetOps Agent atau Hermes) terpasang di host yang sama.
- Port berikut belum dipakai: `3000` (UI), `8200` (manager), `8100` (NetOps Agent), dan `8642` (Hermes). Semua port dapat diubah di `.env`.

### 1. Jalankan backend

**NetOps Agent**

```bash
cd /path/ke/palapa-agent
PALAPA_CONFIG_PATH=$HOME/.palapa/config.yaml \
  uv run uvicorn palapa.gateway.api:app --host 127.0.0.1 --port 8100
```

**Hermes**

Tambahkan baris berikut ke `~/.hermes/.env`, lalu restart gateway Hermes:

```bash
API_SERVER_KEY=<key-acak-yang-kuat>      # buat dengan: openssl rand -hex 32
```

Pastikan backend sudah berjalan sebelum melanjutkan:

```bash
curl -s localhost:8100/health     # NetOps Agent
curl -s localhost:8642/health     # Hermes
```

### 2. Konfigurasi

```bash
git clone https://github.com/LLMNetOps/NetOpsUI.git NetOpsUI && cd NetOpsUI
git checkout ui
cp .env.example .env
nano .env      # atau editor lain
```

Sesuaikan variabel berikut di `.env`:

| Variabel | Isi |
|---|---|
| `NETOPS_AGENT_HOME` | Direktori home NetOps Agent, misalnya `/home/<user>/.palapa` |
| `HERMES_HOME` | Direktori home Hermes, misalnya `/home/<user>/.hermes` |
| `HOST_UID` / `HOST_GID` | Keluaran `id -u` dan `id -g` |
| `NETOPS_AGENT_URL`, `HERMES_URL` | Ubah hanya jika port backend berbeda dari bawaan |

File berikut **harus sudah ada** di host sebelum container dijalankan. Jika belum ada, Docker akan membuatnya sebagai direktori dan proses mount gagal.

- `$NETOPS_AGENT_HOME/SOUL.md`, `config.yaml`, dan `.env`
- `$HERMES_HOME/SOUL.md`, `config.yaml`, dan `.env`

Direktori `data/` sudah tersedia di repositori. Pastikan direktori ini dimiliki oleh user Anda, bukan `root`.

### 3. Build dan jalankan

```bash
docker compose up -d --build
docker compose ps          # service frontend dan manager harus berstatus "healthy"
```

### 4. Buat user pertama

NetOpsUI mewajibkan login dan tidak menyediakan halaman pendaftaran. Buat user melalui CLI:

```bash
docker compose exec manager python create_user.py admin
```

Password minimal 10 karakter. Jika perintah ini dijalankan untuk username yang sudah ada, password user tersebut akan **diatur ulang**.

### 5. Buka UI

Buka `http://<host>:3000`, login, lalu pilih backend di **Settings → Backend**.

Untuk Hermes, tempel juga `API_SERVER_KEY` pada kartu Hermes di halaman yang sama, klik **Cek**, lalu **Simpan**. Key disimpan di database NetOpsUI, bukan di `.env`.

## Catatan

- **Keamanan koneksi:** tanpa HTTPS, password dan cookie sesi dikirim melalui jaringan tanpa enkripsi. Untuk akses dari luar localhost, pasang TLS melalui reverse proxy atau gunakan VPN di depan port `3000`.
- **Credential:** API key Hermes dan LLM provider disimpan di `data/netopsui.db`. Batasi akses ke direktori `data/` beserta salinan cadangannya.
- **Pembaruan:** jalankan `git pull && docker compose up -d --build`. Data di `data/` tidak ikut terhapus.
- **Mode pengembangan (hot reload):** `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`.
- Detail teknis dan aturan pengembangan tersedia di [CLAUDE.md](CLAUDE.md).
