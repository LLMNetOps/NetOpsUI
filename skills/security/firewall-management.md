---
name: firewall-management
domain: security
triggers:
  - tambah firewall rule
  - blokir IP
  - izinkan akses
  - firewall rule
  - tambah rule firewall
  - cek firewall
  - akses diblokir
  - buka port
  - tutup port
  - kelola firewall
  - filter firewall
tools:
  - run_command
  - run_command_write
  - backup_router_config
  - check_reachability
  - get_router_log
approval_required: true
enabled: true
---

# Manajemen Firewall MikroTik

## Konteks
Gunakan skill ini untuk melihat, menambah, dan mengelola aturan firewall di router
kampus MikroTik. Mencakup filter rules (INPUT/FORWARD/OUTPUT chain), address-list,
dan connection tracking.

**PENTING:** Perubahan firewall memerlukan persetujuan operator. Rule yang salah
bisa memblokir akses manajemen ke router atau memutus koneksi pengguna.

## Melihat Aturan Firewall

### Cek Semua Filter Rule
```
/ip/firewall/filter/print
```

### Filter per Chain
```
/ip/firewall/filter/print where chain=input      ← akses ke router itu sendiri
/ip/firewall/filter/print where chain=forward    ← traffic yang lewat router
/ip/firewall/filter/print where chain=output     ← traffic dari router
```

### Cek Address List
```
/ip/firewall/address-list/print
```
Biasanya digunakan untuk: daftar IP yang diblokir, IP manajemen yang diizinkan, IP subnet kampus.

### Cek Connection Tracking
```
/ip/firewall/connection/print count-only
/ip/firewall/connection/print where src-address~"<ip>"
```

## Memahami Struktur Firewall MikroTik

### Chain dan Fungsinya
- **INPUT**: traffic yang ditujukan ke router (SSH, Winbox, ping ke router)
- **FORWARD**: traffic yang melewati router (pengguna internet, antar subnet)
- **OUTPUT**: traffic yang berasal dari router sendiri

### Urutan Rule (PENTING)
Rule diproses dari atas ke bawah. Rule pertama yang cocok → dieksekusi.
Jika tidak ada yang cocok → tergantung default policy (biasanya accept).

**Contoh struktur yang aman untuk chain INPUT:**
```
1. accept - established/related connections (connection-state=established,related)
2. drop   - invalid connections (connection-state=invalid)
3. accept - ICMP dari management subnet (protocol=icmp, src-address=10.0.0.0/8)
4. accept - SSH dari management subnet (dst-port=22, src-address=10.0.0.0/8)
5. accept - Winbox dari management subnet (dst-port=8291, src-address=10.0.0.0/8)
6. drop   - semua yang lain ke input (default deny)
```

## Prosedur Menambah Rule Firewall

### Langkah 1: Backup Config
Selalu backup sebelum mengubah firewall.

### Langkah 2: Rencanakan Rule
Tentukan dengan jelas:
- Chain: input / forward / output
- Action: accept / drop / reject
- Match criteria: src/dst address, port, protocol
- Posisi: di mana dalam urutan rule (gunakan `place-before`)

### Langkah 3: Tambah Rule

**Blokir IP tertentu:**
```
/ip/firewall/filter/add chain=input action=drop src-address=1.2.3.4
  comment="Blokir brute force 1.2.3.4 - 2026-05-09"
  place-before=[find comment="default-drop-input"]
```

**Izinkan akses SSH dari subnet manajemen:**
```
/ip/firewall/filter/add chain=input action=accept protocol=tcp dst-port=22
  src-address=10.0.0.0/8 comment="SSH dari subnet manajemen"
  place-before=[find chain=input action=drop]
```

**Blokir akses ke port tertentu dari luar:**
```
/ip/firewall/filter/add chain=forward action=drop protocol=tcp dst-port=23
  comment="Blokir telnet dari luar kampus"
  in-interface=<wan-interface>
```

### Langkah 4: Verifikasi Posisi Rule
```
/ip/firewall/filter/print
```
Pastikan rule baru berada di posisi yang benar dalam urutan.

### Langkah 5: Test Rule Baru
- Jika baru menambah DROP rule: verifikasi traffic yang seharusnya masih diizinkan tidak terblokir
- Jika baru menambah ACCEPT rule: verifikasi akses yang dimaksud berfungsi
- Cek log: `get_router_log(router_name, topic="firewall", lines=20)`

## Prosedur Blokir IP (Untuk Brute Force / Attack)

Untuk respons cepat terhadap serangan, gunakan address-list:

### Tambah ke Blocklist
```
/ip/firewall/address-list/add list=blacklist address=1.2.3.4
  comment="Brute force detected 2026-05-09 by NOC"
```

### Pastikan Ada Rule yang Memblokir address-list ini
```
/ip/firewall/filter/print where src-address-list=blacklist
```
Jika belum ada rule yang memblokir blacklist → tambahkan:
```
/ip/firewall/filter/add chain=input action=drop
  src-address-list=blacklist comment="Drop semua dari blacklist"
  place-before=0
```

### Hapus dari Blocklist (setelah ancaman berlalu)
```
/ip/firewall/address-list/remove [find address=1.2.3.4 list=blacklist]
```

## Prosedur Menonaktifkan Rule Sementara

Jika rule tertentu menyebabkan masalah, disable dulu tanpa menghapus:
```
/ip/firewall/filter/disable [find comment="nama-rule"]
```

Re-enable:
```
/ip/firewall/filter/enable [find comment="nama-rule"]
```

## Output yang Diharapkan
- Tabel firewall rules yang ada (dengan nomor index)
- Konfirmasi rule berhasil ditambah / diubah / dihapus
- Hasil test akses setelah perubahan
- Nomor backup file sebelum perubahan

## Catatan
- Selalu tambahkan `comment` pada setiap rule baru: isi dengan tujuan + tanggal
- Rule tanpa comment sulit diaudit dan bisa salah dihapus di kemudian hari
- Jangan hapus rule sampai yakin benar rule tersebut yang dimaksud — disable dulu
- Firewall IPv6 ada di `/ipv6/firewall/filter/` — terpisah dari IPv4
- Untuk rate limiting (anti-DDoS): gunakan `/ip/firewall/filter` dengan `limit` matcher
  dan address-list untuk bump ke blocklist
