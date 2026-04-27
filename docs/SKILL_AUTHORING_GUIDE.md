# Skill Authoring Guide — NetOps AI

**Versi:** 1.0  
**Tanggal:** 2026-04-27  
**Audience:** Operator Jaringan

---

## Apa Itu Skill?

Skill adalah file Markdown yang mendefinisikan **pengetahuan domain dan prosedur kerja** untuk agent AI. Operator jaringan menulis skill untuk mengajarkan agent cara menangani situasi spesifik — tanpa perlu menyentuh kode Python.

Ketika operator bertanya *"kenapa Lab5 tidak dapat IP?"*, agent membaca skill `diagnose-dhcp-client` dan mengikuti langkah-langkah yang operator tulis di sana.

---

## Struktur File

Setiap skill adalah satu file `.md` di dalam direktori `skills/`.

```
skills/
├── dhcp/
│   ├── diagnose-dhcp-client.md
│   └── dhcp-pool-audit.md
├── routing/
│   └── bgp-diagnostics.md
├── monitoring/
│   └── network-health-check.md
├── security/
│   └── security-audit.md
└── config/
    └── config-backup-procedure.md
```

Subdirektori berfungsi sebagai **domain kategori** — nama subdirektori bebas, digunakan untuk organisasi saja.

---

## Format Skill

Setiap file skill terdiri dari dua bagian: **frontmatter** dan **body**.

```markdown
---
name: nama-skill-dengan-tanda-hubung
domain: dhcp
triggers:
  - kalimat atau kata kunci yang memicu skill ini
  - bisa lebih dari satu trigger
tools:
  - nama_tool_1
  - nama_tool_2
approval_required: false
enabled: true
---

# Judul Skill yang Deskriptif

## Konteks
Jelaskan kapan dan mengapa skill ini digunakan.

## Prosedur
Jelaskan langkah-langkah yang harus diikuti agent.

## Output yang Diharapkan
Jelaskan format dan isi output yang diinginkan.
```

---

## Frontmatter (YAML)

### Field Wajib

| Field | Tipe | Deskripsi |
|---|---|---|
| `name` | string | Identifier unik, gunakan huruf kecil dan tanda hubung |
| `domain` | string | Kategori domain: `dhcp`, `routing`, `monitoring`, `security`, `config` |
| `triggers` | list | Kata kunci atau frasa yang memicu skill ini dipilih otomatis |

### Field Opsional

| Field | Tipe | Default | Deskripsi |
|---|---|---|---|
| `tools` | list | semua | Tools yang diizinkan untuk skill ini |
| `approval_required` | boolean | `false` | Apakah perlu persetujuan operator sebelum dieksekusi |
| `enabled` | boolean | `true` | Set `false` untuk menonaktifkan skill tanpa menghapus file |

### Contoh Frontmatter

```yaml
---
name: diagnose-dhcp-client
domain: dhcp
triggers:
  - client tidak dapat IP
  - DHCP tidak berfungsi
  - no IP address
  - lease gagal
  - perangkat tidak dapat alamat
tools:
  - search_device
  - get_dhcp_leases
  - get_router_log
  - run_diagnostic
approval_required: false
enabled: true
---
```

---

## Body Markdown

Body skill adalah instruksi dalam bahasa natural yang dibaca dan diikuti oleh agent AI. Tulis seperti menulis **Standard Operating Procedure (SOP)** untuk rekan kerja.

### Sections yang Direkomendasikan

#### `## Konteks`
Kapan skill ini digunakan. Berikan contoh situasi yang memicu skill.

```markdown
## Konteks
Gunakan skill ini saat ada laporan client tidak mendapat IP address
dari DHCP server. Biasanya dipicu oleh keluhan seperti:
"komputer Lab3 tidak bisa connect", "IP address tidak muncul",
atau "DHCP error".
```

#### `## Prosedur`
Langkah-langkah yang harus diikuti agent, berurutan. Boleh bercabang
(if/else) untuk kondisi yang berbeda.

```markdown
## Prosedur

### Langkah 1: Identifikasi Perangkat
Jika diketahui MAC address atau IP, gunakan `search_device` untuk
menemukan perangkat di router mana dan DHCP server apa yang menanganinya.

### Langkah 2: Cek Status Lease
Ambil data lease dari server yang bertanggung jawab.
- Jika status `waiting` → client sedang mencoba tapi gagal
- Jika status `disabled` → entri di-disable secara manual
- Jika tidak ada entri → MAC belum pernah terdaftar, atau pool penuh

### Langkah 3: Cek Log
Ambil log router dengan topic `dhcp`. Cari pesan error:
- `no leases available` → pool IP habis
- `rejected` → ada konflik atau filter

### Langkah 4: Verifikasi Koneksi
Ping dari router ke IP yang seharusnya didapat client.
Jika ada reply → kemungkinan IP conflict dengan perangkat lain.
```

#### `## Output yang Diharapkan`
Format output yang diinginkan operator dari skill ini.

```markdown
## Output yang Diharapkan
Berikan ringkasan diagnosis yang mencakup:
1. Status lease client (bound/waiting/disabled/tidak ada)
2. Penyebab masalah yang teridentifikasi
3. Rekomendasi tindakan konkret

Contoh output yang baik:
"Client MAC XX:XX:XX:XX tidak mendapat IP karena pool `dhcp-lab3`
sudah penuh (273/256 entry). Rekomendasi: nonaktifkan lease lama
yang sudah `waiting` lebih dari 7 hari, atau perluas pool."
```

#### `## Catatan` (opsional)
Hal-hal penting, edge cases, atau peringatan.

```markdown
## Catatan
- DHCP server MikroTik tidak membedakan antara "lease habis" dan
  "client tidak aktif" — keduanya tampil sebagai `waiting`
- Jangan hapus entri `waiting` yang baru (< 1 hari) karena client
  mungkin sedang booting
```

---

## Tools yang Tersedia

Daftar tool yang dapat didefinisikan di frontmatter `tools:`:

### Monitoring & Status
| Tool | Deskripsi |
|---|---|
| `list_routers` | Daftar semua router yang terdaftar |
| `check_reachability` | Cek ping ke router |
| `get_system_info` | CPU, RAM, uptime router |
| `get_interface_traffic` | TX/RX rate realtime per interface |
| `get_traffic_summary` | Ringkasan traffic semua interface |
| `get_top_talkers` | IP dengan traffic tertinggi |
| `get_queue_stats` | Statistik queue dan drop |

### DHCP
| Tool | Deskripsi |
|---|---|
| `get_dhcp_leases` | Data lease satu DHCP server |
| `get_all_leases_for_router` | Semua lease di satu router |
| `search_device` | Cari perangkat by IP atau MAC |
| `audit_all_routers` | Audit DHCP semua router |

### Routing & Interface
| Tool | Deskripsi |
|---|---|
| `get_routing_full` | Routing table + OSPF + BGP lengkap |
| `get_router_config` | Konfigurasi router (berbagai section) |
| `get_interface_stats` | Error dan drop per interface |

### Log
| Tool | Deskripsi |
|---|---|
| `get_router_log` | Log router (bisa filter per topic) |

### Diagnostik
| Tool | Deskripsi |
|---|---|
| `run_diagnostic` | Ping atau traceroute dari router |
| `run_command` | Perintah read-only di satu router |
| `run_command_all_routers` | Perintah yang sama di semua router |

### Config & Backup
| Tool | Deskripsi |
|---|---|
| `backup_router_config` | Backup config router (butuh approval) |
| `list_backups` | Daftar backup tersimpan |
| `diff_config` | Perbedaan dua versi config |

### Security
| Tool | Deskripsi |
|---|---|
| `security_audit` | Audit user, NTP, firewall |

### Laporan
| Tool | Deskripsi |
|---|---|
| `list_reports` | Daftar file laporan |
| `read_report` | Baca laporan Markdown |
| `read_report_section` | Baca section tertentu dari laporan |
| `get_report_toc` | Daftar isi laporan |

---

## Tips Menulis Skill yang Baik

### ✅ Lakukan

- **Tulis triggers yang spesifik** — gunakan frasa yang benar-benar akan diketik operator
- **Berikan contoh output** — agent lebih akurat jika tahu format yang diinginkan
- **Sebutkan edge cases** — kondisi yang tidak biasa perlu instruksi eksplisit
- **Gunakan bahasa operasional** — tulis seperti SOP, bukan tutorial akademis
- **Satu skill, satu masalah** — jangan gabungkan terlalu banyak skenario dalam satu skill

### ❌ Hindari

- Triggers yang terlalu umum (`jaringan`, `cek`, `status`) — terlalu banyak false positive
- Langkah yang ambigu (`cek router`) — lebih baik spesifik (`ping router, cek uptime, lihat log`)
- Menyebutkan tool yang tidak ada di daftar `tools:` frontmatter
- Skill yang duplikat dengan skill lain yang sudah ada

---

## Contoh Skill Lengkap

```markdown
---
name: ospf-neighbor-down
domain: routing
triggers:
  - OSPF neighbor down
  - adjacency hilang
  - routing OSPF bermasalah
  - OSPF tidak full
tools:
  - get_routing_full
  - get_router_config
  - get_router_log
  - check_reachability
  - run_command
approval_required: false
enabled: true
---

# Diagnosa OSPF Neighbor Down

## Konteks
Gunakan skill ini saat ada laporan OSPF adjacency tidak terbentuk
atau neighbor yang sebelumnya Full tiba-tiba turun ke state lain.
Tanda-tanda: beberapa subnet tidak terjangkau, routing tiba-tiba
berubah, atau alert OSPF dari sistem monitoring.

## Prosedur

### Langkah 1: Cek State Neighbor Saat Ini
Gunakan `get_routing_full` untuk melihat semua OSPF neighbor dan
state-nya. Catat neighbor yang tidak dalam state `Full`.

### Langkah 2: Verifikasi Konektivitas Layer 3
Ping dari router yang bermasalah ke IP neighbor-nya.
- Jika tidak reachable → masalah di layer fisik atau IP
- Jika reachable tapi OSPF tidak Full → masalah konfigurasi OSPF

### Langkah 3: Periksa Konfigurasi OSPF
Ambil konfigurasi OSPF kedua router. Bandingkan:
- Area ID harus sama di kedua sisi
- Hello interval dan dead interval harus cocok
- Network type harus sama (broadcast/point-to-point)
- Authentication key jika digunakan

### Langkah 4: Baca Log Router
Cari log dengan topic `ospf` atau `routing`. Pesan yang perlu
diperhatikan:
- `neighbor changed state` → kapan dan dari state apa ke apa
- `authentication failure` → mismatch authentication key
- `dead timer expired` → hello packet tidak diterima

## Output yang Diharapkan
Ringkasan yang mencakup:
- Daftar neighbor yang bermasalah beserta state saat ini
- Penyebab yang paling mungkin (layer 3, konfigurasi, atau timer)
- Rekomendasi langkah perbaikan yang konkret

## Catatan
- RouterOS v7 menggunakan `/routing/ospf/neighbor/print`
- RouterOS v6 menggunakan `routing ospf neighbor print`
- Flap OSPF yang sering (naik-turun) biasanya disebabkan link
  yang tidak stabil atau CPU tinggi di salah satu router
```

---

## Cara Menambah Skill Baru

1. Buat file baru di subdirektori yang sesuai:
   ```
   skills/routing/nama-skill-baru.md
   ```

2. Tulis frontmatter dan body sesuai format di atas

3. Simpan file — skill **langsung aktif** tanpa restart sistem

4. Test dengan mengetik query yang sesuai trigger di TUI AI Chat,
   atau invoke eksplisit dengan `/skill nama-skill-baru`

---

## Cara Menonaktifkan Skill

Set `enabled: false` di frontmatter:

```yaml
---
name: skill-yang-tidak-aktif
enabled: false
---
```

Skill tidak akan dipilih oleh agent, tapi file tetap tersimpan.

---

## Cara Invoke Skill Secara Eksplisit

Di TUI AI Chat, ketik:

```
/skill nama-skill
```

Contoh:
```
/skill diagnose-dhcp-client
/skill bgp-diagnostics
/skill security-audit
```

Agent akan langsung menggunakan skill tersebut tanpa perlu
supervisor mendeteksi intent terlebih dahulu.
