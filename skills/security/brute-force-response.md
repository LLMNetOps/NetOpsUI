---
name: brute-force-response
domain: security
triggers:
  - ada brute force
  - serangan login
  - banyak login failure
  - blokir penyerang
  - IP menyerang router
  - serangan SSH
  - credential stuffing
  - respons insiden keamanan
  - IP harus diblokir
tools:
  - get_router_log
  - run_command
  - run_command_all
  - backup_router_config
  - check_reachability
approval_required: true
enabled: true
---

# Respons Insiden: Brute Force Attack

## Konteks
Gunakan skill ini ketika terdeteksi serangan brute force terhadap router kampus —
banyak `login failure` dari IP yang sama dalam waktu singkat. Skill ini mencakup:
deteksi, analisis, pemblokiran, dan pencegahan jangka panjang.

**Tindakan blokir memerlukan persetujuan operator.** Pemblokiran IP yang salah bisa
memutus akses pengguna atau mitra institusi yang sah.

## Prosedur Deteksi dan Analisis

### Langkah 1: Kumpulkan Log Login Failure
```
get_router_log(router_name, topic="system", lines=100)
```

Atau untuk semua router sekaligus:
```
run_command_all("/log/print where topics~\"system\" and message~\"login failure\"")
```

### Langkah 2: Hitung Login Failure per IP
Analisis log untuk menghitung berapa kali tiap IP gagal login:

**Threshold penilaian:**
| Login Failure | Penilaian | Tindakan |
|--------------|-----------|---------|
| 1-3x | Normal (salah ketik) | Monitor saja |
| 4-10x | Curigai | Catat, cek apakah masih berlanjut |
| 11-50x | Kemungkinan serangan | Blokir sementara |
| > 50x | Serangan aktif | Blokir segera + lapor |

### Langkah 3: Identifikasi Pola Serangan
Dari timestamp log, tentukan pola:
- **Burst singkat** (semua dalam < 1 menit): credential stuffing otomatis
- **Bertahap lambat** (beberapa per jam): serangan manual atau low-rate bot
- **Berulang dari subnet berbeda**: coordinated attack / botnet
- **Username yang dicoba**: `admin`, `root`, `user` → serangan acak; nama admin spesifik → targeted

Catat dan laporkan ke operator:
```
Temuan: IP 1.2.3.4 melakukan 127x login failure ke GATE-X dalam 3 menit
Username yang dicoba: admin, administrator, root, netops
Pola: burst otomatis (credential stuffing)
Penilaian: SERANGAN AKTIF — rekomendasikan blokir segera
```

## Prosedur Pemblokiran

### Pemblokiran via Address-List (Direkomendasikan)

**Langkah 1: Pastikan ada rule yang menggunakan blacklist**
Cek apakah sudah ada rule DROP untuk address-list `blacklist`:
```
/ip/firewall/filter/print where src-address-list=blacklist
```
Jika belum ada → tambahkan dulu (lihat skill `firewall-management`).

**Langkah 2: Backup**
```
backup_router_config(router_name)
```

**Langkah 3: Tambah IP ke Blacklist**
```
/ip/firewall/address-list/add list=blacklist address=1.2.3.4
  comment="Brute force 127x login failure - 2026-05-09 NOC"
```

Untuk memblokir subnet (jika serangan dari /24):
```
/ip/firewall/address-list/add list=blacklist address=1.2.3.0/24
  comment="Subnet brute force - 2026-05-09 NOC"
```

**Langkah 4: Verifikasi Blokir Aktif**
```
/ip/firewall/address-list/print where list=blacklist
```
Kemudian monitor log — login failure dari IP tersebut harus berhenti.

### Pemblokiran Cepat (Rule Langsung)
Untuk respons sangat cepat sebelum address-list siap:
```
/ip/firewall/filter/add chain=input action=drop src-address=1.2.3.4
  comment="Emergency block brute force - 2026-05-09" place-before=0
```

## Prosedur Pencegahan Jangka Panjang

### 1. Auto-Blokir dengan Script MikroTik
Konfigurasikan router untuk otomatis blokir IP yang gagal login > N kali:

```
/ip/firewall/filter/add chain=input action=add-src-to-address-list
  protocol=tcp dst-port=22 address-list=ssh-stage1
  address-list-timeout=1m connection-state=new
  comment="SSH brute force detect stage 1"

/ip/firewall/filter/add chain=input action=add-src-to-address-list
  protocol=tcp dst-port=22 src-address-list=ssh-stage1
  address-list=ssh-blacklist address-list-timeout=1d
  connection-state=new
  comment="SSH brute force — auto blacklist 24 jam"

/ip/firewall/filter/add chain=input action=drop
  src-address-list=ssh-blacklist
  comment="Drop SSH brute force blacklist"
```

### 2. Batasi Port SSH ke Subnet Manajemen
Jika SSH hanya boleh dari subnet internal:
```
/ip/firewall/filter/add chain=input action=accept protocol=tcp dst-port=22
  src-address=10.0.0.0/8 comment="SSH dari subnet kampus"

/ip/firewall/filter/add chain=input action=drop protocol=tcp dst-port=22
  comment="Blokir SSH dari luar kampus"
```

### 3. Ganti Port SSH Default
Ubah dari port 22 ke port non-standar (misalnya 2222):
```
/ip/service/set ssh port=2222
```
Bukan solusi sempurna tapi signifikan mengurangi noise dari bot scanner.

### 4. Aktifkan Login Failure Logging
Pastikan logging aktif untuk system events:
```
/system/logging/print
```
Harus ada rule: `topics=system` ke log output.

## Output yang Diharapkan
- Laporan analisis: jumlah login failure per IP, pola serangan, router yang terdampak
- Daftar IP yang diblokir beserta alasannya
- Konfirmasi rule firewall aktif
- Rekomendasi pencegahan jangka panjang

## Catatan
- Sebelum blokir subnet besar (/24 atau lebih): verifikasi tidak ada IP kampus yang sah di subnet tersebut
- IP blokir dengan timeout akan otomatis dihapus setelah periode tertentu — cocok untuk blokir sementara
- IP blokir tanpa timeout = permanen — gunakan untuk IP yang berulang kali menyerang
- Insiden serangan yang signifikan (> 1000 attempt, targeted, dari sumber terdistribusi)
  → laporkan ke CERT/CC atau IDREN-NOC
- Simpan semua blokir ke log keamanan untuk audit dan analisis tren


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
| IP attacker teridentifikasi — perlu blokir | Serahkan IP + perintah firewall drop | config_agent |
| Perlu laporan insiden | Serahkan IP, timestamp, frekuensi | document_agent |
| False positive / sudah diblokir | Tidak perlu handoff | END |
