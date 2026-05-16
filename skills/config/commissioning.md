---
name: commissioning
domain: config
triggers:
  - komisioning
  - commissioning
  - komisioning router
  - komisioning lab
  - konfigurasi router baru
  - setup router baru
  - inisialisasi router
tools:
  - get_report
  - list_routers
  - check_reachability
  - run_command
  - run_command_write
  - get_system_info
approval_required: true
enabled: true
---

# Commissioning Router — Konfigurasi Awal dari Fresh State

## Konteks

Skill ini mengeksekusi konfigurasi awal router RouterOS CHR dari kondisi fresh (default admin/kosong).
Semua parameter dikonfigurasi berdasarkan dokumen spec yang dibaca dari `laporan/commissioning-spec-lab.md`.

## Aturan Kritis

- BACA spec dulu sebelum mengeksekusi apapun
- Konfigurasi satu router sampai selesai sebelum pindah ke router berikutnya
- Setiap langkah butuh approval operator (run_command_write)
- Jika satu langkah gagal: catat error, lanjut ke langkah berikutnya, flag di laporan akhir
- JANGAN skip validasi — validasi wajib setelah semua konfigurasi selesai

## Prosedur

### Langkah 0: Baca Spec

Panggil `get_report("commissioning-spec-lab")`.

Ekstrak dari spec:
- Daftar router (nama + host mgmt + interface link)
- IP addressing plan per router
- Parameter konfigurasi (NTP, SNMP, user, dll)
- Urutan konfigurasi yang harus diikuti

**→ SETELAH BACA SPEC: LANGSUNG cek reachability semua router. JANGAN tulis apapun dulu.**

### Langkah 1: Cek Reachability Awal

Panggil `check_reachability(router_name)` untuk setiap router di spec.

- Router up → lanjut komisioning
- Router down → catat, skip komisioning router ini, lanjut ke router berikutnya

**→ LANGSUNG mulai konfigurasi untuk setiap router yang up.**

### Langkah 2: Konfigurasi per Router

Untuk setiap router yang reachable, eksekusi urutan berikut via `run_command_write`:

**2a. IP Address ether2**
```
/ip address add address=<IP_dari_spec> interface=ether2
```

**2b. Loopback Interface**
```
/interface bridge add name=loopback
/ip address add address=<IP_loopback_dari_spec> interface=loopback
```

**2c. Tambah User**
```
/user add name=<username_dari_spec> password=<password_dari_spec> group=full
```

**2d. NTP**
```
/system clock set time-zone-name=<timezone_dari_spec>
/system ntp client set enabled=yes servers=<ntp_server_dari_spec>
```

**2e. SNMP**
```
/snmp set enabled=yes contact=<contact_dari_spec> location=<location_dari_spec>
/snmp community set [ find name=public ] read-access=yes
```

**2f. Static Routing**
```
/ip route add dst-address=<dst_dari_spec> gateway=<gw_dari_spec>
```

Semua nilai HARUS dari hasil `get_report` di Langkah 0 — JANGAN hardcode.

### Langkah 3: Validasi

Setelah semua router selesai dikonfigurasi, validasi berdasarkan tabel kriteria di spec:

Untuk setiap router, jalankan:
1. `check_reachability(router_name)` — konfirmasi masih up
2. `run_command(router_name, "/ip address print")` — verifikasi IP terpasang
3. `run_command(router_name, "/user print")` — verifikasi user ada
4. `run_command(router_name, "/system ntp client print")` — verifikasi NTP
5. `run_command(router_name, "/snmp print")` — verifikasi SNMP
6. `run_command(router_name, "/ip route print")` — verifikasi static route
7. `run_command(router_name, "/ping <loopback_peer> count=3")` — end-to-end connectivity

**→ SETELAH VALIDASI SELESAI: handoff ke document_agent untuk buat laporan.**

## Format Ringkasan ke document_agent

Sertakan dalam handoff:
- Daftar router yang berhasil dikonfigurasi vs gagal
- Tabel hasil validasi per router (✅/🚨 per kriteria)
- Error yang ditemukan selama konfigurasi
- Waktu mulai dan selesai

## Catatan

- Skill ini hanya untuk lab (containerlab). Jangan digunakan untuk router produksi tanpa review.
- Setelah komisioning selesai, operator perlu update `network: lab` → network produksi di config.yaml jika router dipindah ke produksi.
- Containerlab topology dan cara deploy ada di bagian 7 dari commissioning-spec-lab.md.
