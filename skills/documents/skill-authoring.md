---
name: skill-authoring
domain: documents
triggers:
  - buat skill baru
  - tulis skill
  - tambah skill
  - tambahkan skill
  - buat prosedur baru
  - ajarkan agent cara
  - tambah pengetahuan agent
  - create new skill
  - write skill
tools:
  - write_skill
approval_required: false
enabled: true
---

# Menulis Skill Baru

## Konteks
Gunakan skill ini saat operator meminta membuat skill baru untuk mengajarkan agent cara
menangani situasi spesifik di jaringan kampus. Skill yang ditulis **langsung aktif** tanpa
restart — berkat hot-reload via watchfiles.

## Prosedur

### Langkah 1: Kumpulkan Informasi dari Operator
Jika belum jelas dari percakapan, tanyakan:
- **Masalah apa** yang ingin ditangani skill ini?
- **Domain** mana yang paling sesuai: `dhcp`, `routing`, `monitoring`, `security`, `config`, atau `documents`?
- **Tools** apa yang perlu digunakan agent? (opsional — bisa disarankan)

Jika operator sudah menjelaskan cukup, lanjut langsung ke Langkah 2.

### Langkah 2: Tentukan Nama dan Triggers

**Penamaan** mengikuti pola `[domain]-[capability-noun]`:
```
✓ ospf-diagnostics        ← domain + capability noun
✓ dhcp-client-diagnostics
✓ network-traffic-analysis
✗ diagnose-ospf           ← kata kerja di depan
✗ ospf-neighbor-down      ← terlalu spesifik ke satu kondisi
```

**Triggers** harus mencakup:
- Frasa yang akan diketik operator (bahasa natural)
- Variasi singkat dan panjang
- Istilah teknis yang relevan

### Langkah 3: Pilih Tools

Pilih tools yang relevan dari daftar berikut berdasarkan domain skill:

| Domain | Tools Utama |
|--------|-------------|
| monitoring | `check_reachability`, `get_system_info`, `get_interface_stats`, `get_traffic_all` |
| dhcp | `get_dhcp_leases`, `get_router_leases`, `audit_dhcp`, `search_device` |
| routing | `get_routing_full`, `get_router_config`, `get_router_log`, `run_command` |
| security | `audit_security`, `get_router_log`, `run_command` |
| config | `get_router_config`, `backup_router_config`, `list_backups`, `diff_config` |
| documents | `write_document`, `list_templates`, `read_template`, `write_skill` |

Tools yang dicantumkan di frontmatter skill **harus dimiliki oleh agent** yang menggunakan skill ini.

### Langkah 4: Susun Body Skill

Tulis body mengikuti struktur ini:

```markdown
## Konteks
[Kapan skill ini digunakan. Sertakan contoh gejala atau trigger situasi.]

## Prosedur

### Langkah 1: [Nama Langkah]
[Instruksi spesifik. Sebutkan tool yang dipakai dan apa yang dicari dari hasilnya.]

### Langkah N: [Nama Langkah]
[Lanjutan...]

## Output yang Diharapkan
[Format dan isi output yang diinginkan operator — berikan contoh konkret jika bisa.]

## Catatan
[Edge cases, peringatan, atau perbedaan RouterOS v6 vs v7 jika relevan.]
```

### Langkah 5: Simpan dengan write_skill

Panggil `write_skill(domain, name, content)`:
- `domain` = subfolder (contoh: `routing`, `dhcp`)
- `name` = nama file tanpa ekstensi (contoh: `ospf-diagnostics`)
- `content` = seluruh konten Markdown — frontmatter (`---`) + body

Contoh pemanggilan:
```
write_skill(
  domain="routing",
  name="ospf-diagnostics",
  content="---\nname: ospf-diagnostics\n..."
)
```

### Langkah 6: Konfirmasi ke Operator

Setelah berhasil, sampaikan:
- Nama file yang disimpan (`skills/{domain}/{name}.md`)
- Trigger yang akan mengaktifkan skill
- Tools yang digunakan skill ini

## Catatan
- Skill **langsung aktif** setelah disimpan — tidak perlu restart
- Gunakan `approval_required: false` sebagai default untuk skill baru
- Jika skill untuk operasi berisiko (backup, delete), set `approval_required: true`
- Field `enabled: true` wajib agar skill dipilih otomatis oleh supervisor
