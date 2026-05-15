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
  - fetch_url
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

### Langkah 1: Ambil Referensi (jika ada URL)
Jika operator menyertakan URL referensi (GitHub, dokumentasi vendor, dll), ambil lebih dulu:

```
fetch_url("https://raw.githubusercontent.com/user/repo/main/file.md")
```

Tips URL GitHub: gunakan `raw.githubusercontent.com` agar langsung dapat plain text tanpa HTML.
Baca konten, identifikasi bagian yang relevan, gunakan sebagai dasar prosedur skill.

### Langkah 2: Tentukan Apakah Perlu Bertanya

**Default: LANGSUNG BUAT tanpa bertanya** — jika operator menyebut topik teknis yang jelas.

Topik yang cukup jelas untuk langsung dibuat (tidak perlu bertanya):
- Protokol jaringan: MTU, VLAN, OSPF, BGP, DHCP, STP, LACP, VPN
- Kondisi jaringan: flapping, down, unreachable, high CPU, memory penuh
- Operasi spesifik: backup, monitoring, audit, diagnosa, blokir, routing

**Bertanya HANYA jika** permintaan benar-benar ambigu dan tidak bisa ditebak topiknya,
misalnya: "buat skill baru" (tanpa konteks apapun).

### Langkah 3: Tentukan Nama dan Triggers

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

### Langkah 4: Pilih Tools

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

### Langkah 5: Susun Body Skill

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

### Langkah 6: Simpan dengan write_skill

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

### Langkah 7: Konfirmasi ke Operator

Setelah berhasil, sampaikan:
- Nama file yang masuk antrian: `skills/.pending/{domain}/{name}.md`
- Trigger yang akan mengaktifkan skill (setelah diapprove)
- Tools yang digunakan skill ini
- Instruksi untuk review dan approve:
  ```
  python tests/review.py show {name}
  python tests/review.py approve {name}
  ```

Tekankan: **skill belum aktif sampai operator menjalankan approve**.

## Catatan
- Skill ditulis agent masuk ke `skills/.pending/` — **belum aktif**
- Operator harus review di Claude Code, lalu jalankan `python tests/review.py approve <name>`
- Setelah approve, skill langsung aktif via hot-reload — tidak perlu restart
- Gunakan `approval_required: false` sebagai default untuk skill baru
- Jika skill untuk operasi berisiko (backup, delete), set `approval_required: true`
- Field `enabled: true` wajib agar skill dipilih otomatis oleh supervisor

---

## Prinsip untuk Model Kecil (qwen3.5:9b)

Skill ini dieksekusi oleh qwen3.5:9b, bukan GPT-4. Gaya penulisan yang bekerja untuk
model besar sering **gagal** di model kecil. Gunakan tabel ini sebagai panduan:

| Yang Tidak Bekerja | Yang Bekerja |
|--------------------|--------------|
| "Analisis dengan bijak" | "Jika X maka Y. Jika Z maka W." |
| Penjelasan konseptual panjang | Contoh konkret dengan data nyata |
| Instruksi negatif saja ("jangan...") | Instruksi negatif + alternatif positif |
| Satu skill untuk banyak kasus | Satu skill, satu kasus, satu alur linear |
| "Pertimbangkan faktor-faktor yang relevan" | "Periksa CPU, Memory, Uptime secara berurutan" |
| Instruksi ambigu tentang kapan selesai | "Setelah semua router dicek, tulis ringkasan" |

### Aturan Utama

**1. Satu alur linear, bukan pohon keputusan.**
Model kecil tidak baik dalam mengelola percabangan kompleks. Tulis prosedur sebagai
urutan langkah wajib, bukan "jika kondisi A, lakukan X; jika kondisi B, lakukan Y".
Kecuali kondisi benar-benar sederhana dan mutual exclusive.

**2. Sebutkan tool secara eksplisit di setiap langkah.**
Jangan tulis "ambil data yang diperlukan". Tulis:
```
Langkah 1: Jalankan get_bgp_sessions(router_name)
Langkah 2: Periksa kolom "St" — ✓EST berarti normal, ✗DWN berarti masalah
```

**3. Berikan contoh output tool dan cara interpretasinya.**
Model kecil sering bingung apa yang harus dicari dari output. Contoh konkret
mengurangi ambiguitas secara dramatis:
```
Output get_bgp_sessions akan terlihat seperti:
  1  ✓EST  ebgp  7713  103.22.20.1  14d02h  45000  IDREN-upstream
  2  ✗DWN  ebgp  45678  203.45.67.1  —       0      backup-link
Cari baris dengan ✗DWN — itu session yang bermasalah.
```

**4. Output yang diharapkan harus spesifik dan terstruktur.**
Bukan: "Buat laporan yang lengkap dan informatif."
Tapi:
```
Output akhir harus berisi:
- Tabel: Router | BGP Sessions | Status
- Satu paragraf ringkasan kondisi routing
- Jika ada session DOWN: daftar nama session dan remote IP-nya
```

**5. Jaga panjang skill di bawah 150 baris.**
Skill yang terlalu panjang melebihi context window efektif model saat digabung
dengan system prompt agent. Jika terlalu panjang, pecah menjadi dua skill terpisah.

---

## Checklist Review Sebelum Commit

Sebelum menyimpan skill baru atau update, verifikasi:

- [ ] **Nama file** mengikuti pola `[domain]-[capability-noun]` (bukan kata kerja di depan)
- [ ] **Triggers** mencakup variasi bahasa natural yang akan diketik operator
- [ ] **Tools di frontmatter** sesuai dengan tools yang benar-benar dipakai di body
- [ ] **Setiap langkah** menyebut nama tool secara eksplisit
- [ ] **Ada contoh output** untuk setidaknya satu tool utama
- [ ] **Output yang diharapkan** ditulis konkret, bukan deskriptif
- [ ] **Panjang skill** di bawah 150 baris
- [ ] **Tidak ada instruksi ambigu** seperti "analisis dengan bijak" atau "pertimbangkan faktor"
- [ ] Jalankan `python tests/eval.py` — pastikan scenario terkait tetap pass


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
| Skill baru berhasil ditulis | Tidak perlu handoff | END |
