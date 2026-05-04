---
name: write-report
domain: documents
triggers:
  - simpan laporan
  - tulis laporan ke file
  - ekspor laporan
  - buat dokumen laporan
  - simpan ke file
  - export laporan
  - laporan tertulis
  - dokumentasikan
  - buat file laporan
  - write report
  - save report
tools:
  - list_templates
  - read_template
  - write_document
  - create_template
  - list_reports
  - get_report
approval_required: false
enabled: true
---

# Menulis Dokumen Laporan

## Konteks
Gunakan skill ini saat operator meminta laporan disimpan ke file, atau saat
document_agent perlu mengkompilasi hasil dari beberapa agent menjadi satu dokumen.

## Prosedur

### Langkah 1: Pilih Template
Jalankan `list_templates()` untuk melihat template yang tersedia.
Pilih template yang sesuai dengan jenis laporan:
- `security-assessment.md` → penilaian keamanan aplikasi web / router (blank template berplaceholder)

Jalankan `read_template(name)` untuk memuat struktur template.

**Referensi contoh laporan nyata:** Gunakan `list_reports()` dan `get_report(name)` untuk membaca
laporan sebelumnya di direktori `laporan/` sebagai acuan format dan tingkat detail:
- `security-assessment_teknik-ub_20260430.md` → contoh laporan penilaian keamanan web lengkap

### Langkah 2: Kumpulkan Data
Kumpulkan semua data yang diperlukan menggunakan tools yang tersedia.
Jika agent lain sudah menjalankan analisis sebelumnya, gunakan hasil mereka
dari konteks percakapan — tidak perlu mengumpulkan ulang data yang sama.

### Langkah 3: Susun Dokumen
Isi template dengan data yang sudah dikumpulkan. Pastikan:
- Semua section template terisi lengkap
- Data akurat sesuai hasil tools (bukan asumsi)
- Format konsisten: tabel, kode block, severity icon (🔴🟡🟢ℹ️)
- Timestamp WIB dicantumkan di header

### Langkah 4: Simpan ke File
Gunakan `write_document(filename, content)` dengan konvensi penamaan:

```
{tipe-laporan}_{YYYYMMDD}_{HHMMSS}.md
```

Contoh nama file:
- `network-health_20260501_143022.md`
- `security-report_DTI_20260501_090000.md`
- `dhcp-audit_20260501_120000.md`
- `incident_{nama-insiden}_20260501_153000.md`

## Membuat Template Baru
Jika tidak ada template yang sesuai, gunakan `create_template(name, content)`.
Template baru langsung tersedia untuk semua agent tanpa restart.

Struktur template yang baik:
1. Header metadata (target, tanggal, penguji/operator, scope)
2. Daftar isi
3. Ringkasan eksekutif
4. Section konten utama (sesuai domain)
5. Matriks/ringkasan temuan
6. Rekomendasi prioritas
7. Lampiran (jika perlu)
