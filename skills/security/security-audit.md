---
name: security-audit
domain: security
triggers:
  - audit keamanan
  - cek user router
  - security audit
  - cek NTP
  - ada user tidak dikenal
  - audit akun router
  - cek konfigurasi keamanan
  - hardening router
  - cek login failure
  - ada brute force
  - cek service router
  - audit firewall
tools:
  - audit_security
  - get_router_log
  - run_command
  - run_command_all
approval_required: false
enabled: true
---

# Security Audit Router

## Konteks
Gunakan skill ini untuk memeriksa postur keamanan router jaringan kampus. Mencakup:
cek akun pengguna, status NTP, deteksi brute force, audit layanan yang terbuka, dan
pemeriksaan firewall. Jalankan secara rutin (mingguan) atau setelah ada insiden keamanan.

## Prosedur

### Langkah 1: Audit Menyeluruh
Jalankan `audit_security` tanpa argumen (default: semua router). Fungsi ini memeriksa:
- Daftar user yang ada di tiap router
- Status sinkronisasi NTP
- Keberadaan akun `admin` default (risiko keamanan)

### Langkah 2: Analisis Temuan User
Dari hasil audit, perhatikan:
- Router yang masih memiliki akun `admin` default → wajib diganti namanya atau dihapus
- Jumlah user yang tidak wajar (> 3) → verifikasi apakah semua user dikenal dan sah
- Untuk router tertentu, gunakan `run_command` dengan `/user/print` untuk melihat detail
  level akses (full, read, write, policy) dan alamat IP yang diizinkan

### Langkah 3: Analisis NTP
Router yang tidak sinkron NTP berisiko:
- Log timestamp tidak akurat → menyulitkan forensik
- Sertifikat SSL/TLS bisa ditolak jika waktu terlalu jauh berbeda
- Autentikasi berbasis waktu (Kerberos, dll) bisa gagal

Untuk router dengan NTP tidak sinkron, gunakan `run_command` dengan
`/system/ntp/client/print` untuk melihat server NTP yang dikonfigurasi dan statusnya.

### Langkah 4: Deteksi Brute Force dan Anomali Login
Ambil log dengan `get_router_log(router_name, topic="system", lines=100)`. Analisis:

**Deteksi brute force:**
- Hitung `login failure` per IP sumber
- **> 3 kali dari IP yang sama** → ⚠ kemungkinan brute force — catat IP-nya
- **> 10 kali dari IP yang sama** → ✗ serangan aktif — rekomendasikan blokir segera
- Pola burst (banyak failure dalam hitungan detik) = credential stuffing otomatis

**Anomali login:**
- `logged in` dari IP publik yang tidak dikenal → verifikasi ke operator
- `user added` atau `user removed` → perubahan akun tidak terjadwal
- SSH login berhasil dari luar subnet manajemen → wajib dilaporkan

**Format analisis log:**
```
IP 1.2.3.4 — login failure: 47x di ROUTER-X → ✗ BLOKIR SEGERA
IP 10.0.1.5 — login failure: 2x di ROUTER-Y → ✓ normal (mungkin typo)
IP 103.1.2.3 — logged in 1x (asing) → ⚠ verifikasi ke operator
```

### Langkah 5: Audit Layanan yang Terbuka
Gunakan `run_command(router_name, "/ip/service/print")` untuk memeriksa layanan aktif:

| Layanan | Port | Status Ideal |
|---------|------|--------------|
| ssh     | 22   | enabled, restricted ke subnet mgmt |
| winbox  | 8291 | disable jika tidak dipakai |
| telnet  | 23   | HARUS disabled — plain text |
| ftp     | 21   | HARUS disabled — plain text |
| api     | 8728 | disable jika tidak dipakai |
| api-ssl | 8729 | OK jika dipakai dengan certificate |
| www     | 80   | redirect ke www-ssl atau disable |
| www-ssl | 443  | OK jika dipakai |

Layanan yang enabled tapi tidak perlu → rekomendasikan disable.

### Langkah 6: Audit Firewall Input Chain
Gunakan `run_command(router_name, "/ip/firewall/filter/print where chain=input")`:
- Pastikan ada aturan yang membatasi akses SSH/Winbox ke subnet manajemen
- Pastikan ada aturan DROP di akhir chain input (default deny)
- Identifikasi aturan `accept` yang terlalu luas (dst-address tidak dibatasi)
- Catat aturan yang disabled — mungkin bypass keamanan yang tidak disengaja

Jika tidak ada aturan eksplisit untuk SSH → akses manajemen terbuka ke semua IP → HIGH RISK.

### Langkah 7: Cek Port Scanning / Reconnaissance
Di log system, cari pola:
- Banyak koneksi dari 1 IP ke port berbeda dalam < 1 menit → kemungkinan port scan
- `connection rejected` berulang dari IP yang sama → probe aktif
- `firewall dropped` spike tiba-tiba → bisa DDoS atau scan masif

## Output yang Diharapkan
Laporan audit yang mencakup:
- Status setiap router: NTP synced/not, jumlah user, ada/tidak default admin
- Daftar IP dengan login failure > 3 dan rekomendasinya
- Layanan yang sebaiknya dinonaktifkan
- Celah firewall yang ditemukan
- Tingkat risiko keseluruhan: LOW / MEDIUM / HIGH

Format temuan per router:
```
[ROUTER-NAME]
  ⚠ Akun 'admin' default masih ada — ganti nama atau hapus
  ✗ NTP tidak sinkron (server: 0.id.pool.ntp.org) — cek koneksi ke NTP server
  ✗ Brute force dari 1.2.3.4: 47x login failure — blokir di firewall
  ⚠ Service telnet enabled (port 23) — plaintext, disable segera
  ⚠ Tidak ada firewall rule membatasi akses SSH — semua IP bisa akses
```

## Catatan
- Perubahan konfigurasi memerlukan akses write — gunakan skill `firewall-management`
  atau `config-change` untuk eksekusi
- Blokir IP brute force: gunakan skill `brute-force-response` untuk prosedur lengkap
- Audit security sebaiknya dilakukan dari jaringan manajemen yang terisolasi
- Simpan hasil audit ke laporan menggunakan template `security-assessment.md`
