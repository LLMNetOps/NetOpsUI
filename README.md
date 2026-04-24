# MikroTik DHCP Lease Monitoring Agent

Mengambil data DHCP lease dari beberapa router MikroTik via SSH secara paralel dan menghitung jumlah perangkat aktif yang terkoneksi jaringan UTBK.

## Setup

```bash
# 1. Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependensi
pip install -r requirements.txt

# 3. Isi konfigurasi router
cp config.yaml.example config.yaml   # atau edit langsung config.yaml
# → Isi password SSH dan nama DHCP server yang sesuai
```

## Konfigurasi (`config.yaml`)

```yaml
ssh:
  username: netadmin
  password: "passwordanda"   # atau kosongkan → akan ditanya saat run
  timeout: 15
  port: 22

routers:
  - name: DTI
    host: 10.39.0.1
    dhcp_servers:
      - dhcp-lab-tik

  - name: Gedung-B
    host: 10.32.8.1
    dhcp_servers:
      - dhcp-lab-utbk   # sesuaikan nama DHCP server
```

> ⚠️ **Jangan commit `config.yaml`** — sudah di-ignore via `.gitignore`.

## Penggunaan

```bash
# Aktifkan venv dulu
source .venv/bin/activate

# Jalankan agent (query semua router)
python mikrotik_agent.py

# Dengan detail daftar semua lease
python mikrotik_agent.py --detail

# Test parser tanpa SSH (dari file lokal)
python mikrotik_agent.py --dry-run dhcp-lease-dti.txt

# Tanpa menyimpan file output
python mikrotik_agent.py --no-save
```

## Output

- **Terminal** — Tabel ringkasan jumlah `bound`, `waiting`, `disabled` per router
- **`output/`** — Raw output per router + file summary dengan timestamp

## Struktur Project

```
mikrotik-cek-lease/
├── mikrotik_agent.py   # Agent utama
├── config.yaml         # Konfigurasi (tidak di-commit)
├── requirements.txt    # Dependensi Python
├── .venv/              # Virtual environment
└── output/             # Hasil run (auto-dibuat)
```

## Logika Penghitungan

| Kondisi | Dihitung sebagai |
|---|---|
| Status `bound`, tanpa flag `X` | ✅ Perangkat aktif/connected |
| Status `waiting`, tanpa flag `X` | ⏳ Lease lama, tidak aktif |
| Flag `X` (disabled) | ❌ Tidak dihitung |
