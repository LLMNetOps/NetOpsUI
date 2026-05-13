# Laporan Penilaian Keamanan {{TIPE_TARGET}}
## {{NAMA_TARGET}} — {{UNIT_ORGANISASI}}

---

| Atribut | Detail |
|---|---|
| **Target** | `{{TARGET_URL}}` |
| **Tanggal Pengujian** | {{TANGGAL_PENGUJIAN}} |
| **Penguji** | {{PENGUJI}} |
| **Tipe Pengujian** | {{TIPE_PENGUJIAN}} |
| **Tools** | {{TOOLS_DIGUNAKAN}} |
| **Scope** | {{SCOPE_PENGUJIAN}} |
| **Catatan** | {{CATATAN}} |

---

## Daftar Isi

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Teknologi Stack](#2-teknologi-stack)
3. [Metodologi Pengujian](#3-metodologi-pengujian)
4. [Peta Proteksi / Filtering](#4-peta-proteksi--filtering)
5. [Temuan Keamanan](#5-temuan-keamanan)
6. [Matriks Risiko](#6-matriks-risiko)
7. [Rekomendasi Prioritas](#7-rekomendasi-prioritas)
8. [Lampiran — Bukti Teknis](#8-lampiran--bukti-teknis)

---

## 1. Ringkasan Eksekutif

{{NARASI_SINGKAT_PENGUJIAN_DAN_TEMUAN_UTAMA}}

Ditemukan **{{JUMLAH_TOTAL_TEMUAN}} temuan** dengan distribusi:

| Severity | Jumlah |
|---|---|
| HIGH | {{JUMLAH_HIGH}} |
| MEDIUM | {{JUMLAH_MEDIUM}} |
| LOW | {{JUMLAH_LOW}} |
| INFORMATIONAL | {{JUMLAH_INFO}} |

**Temuan paling kritis:**
- {{TEMUAN_KRITIS_1}}
- {{TEMUAN_KRITIS_2}}
- {{TEMUAN_KRITIS_3}}

---

## 2. Teknologi Stack

{{NARASI_PEMETAAN_TEKNOLOGI}}

```
{{DIAGRAM_ARSITEKTUR_ATAU_STACK}}
```

### 2.1 Komponen Teridentifikasi

| Komponen | Tipe | Versi | Bukti Deteksi |
|---|---|---|---|
| {{KOMPONEN_1}} | {{TIPE_1}} | {{VERSI_1}} | {{BUKTI_1}} |
| {{KOMPONEN_2}} | {{TIPE_2}} | {{VERSI_2}} | {{BUKTI_2}} |

### 2.2 HTTP Headers Teridentifikasi

| Header | Nilai | Signifikansi |
|---|---|---|
| `{{HEADER_1}}` | {{NILAI_1}} | {{KETERANGAN_1}} |
| `{{HEADER_2}}` | {{NILAI_2}} | {{KETERANGAN_2}} |

---

## 3. Metodologi Pengujian

Pengujian dilakukan dalam {{JUMLAH_FASE}} fase:

### Fase 1 — {{NAMA_FASE_1}}

**Tujuan:** {{TUJUAN_FASE_1}}

**Langkah:**
- {{LANGKAH_1}}

**Temuan:**
- {{TEMUAN_FASE_1}}

**Request kunci:**
```http
{{CONTOH_REQUEST_1}}
```

**Respons:**
```
{{CONTOH_RESPONSE_1}}
```

---

### Fase 2 — {{NAMA_FASE_2}}

**Tujuan:** {{TUJUAN_FASE_2}}

**Temuan:**

| Path/Endpoint | Status | Akses |
|---|---|---|
| `{{ENDPOINT_1}}` | {{STATUS_1}} | {{AKSES_1}} |
| `{{ENDPOINT_2}}` | {{STATUS_2}} | {{AKSES_2}} |

---

<!-- Tambahkan fase-fase selanjutnya sesuai metodologi yang digunakan -->

---

## 4. Peta Proteksi / Filtering

```
REQUEST
  │
  ├─► {{KATEGORI_BLOKIR_1}}
  │         → {{JENIS_BLOKIR_1}}
  │
  ├─► {{KATEGORI_BLOKIR_2}}
  │         → {{JENIS_BLOKIR_2}}
  │
  └─► {{KATEGORI_PASS}}
            → {{JENIS_PASS}} ← titik rawan
```

---

## 5. Temuan Keamanan

---

### T-01 | {{JUDUL_TEMUAN_1}}

| Atribut | Detail |
|---|---|
| **Severity** | {{SEVERITY_ICON}} {{SEVERITY_1}} |
| **OWASP** | {{OWASP_1}} |
| **CWE** | {{CWE_1}} |
| **CVSS Base** | {{CVSS_1}} |

**Deskripsi:**

{{DESKRIPSI_TEMUAN_1}}

**Bukti:**
```http
{{BUKTI_REQUEST_1}}

{{BUKTI_RESPONSE_1}}
```

**Dampak:**

{{DAMPAK_TEMUAN_1}}

**Rekomendasi:**
{{REKOMENDASI_TEMUAN_1}}

---

### T-02 | {{JUDUL_TEMUAN_2}}

| Atribut | Detail |
|---|---|
| **Severity** | {{SEVERITY_ICON}} {{SEVERITY_2}} |
| **OWASP** | {{OWASP_2}} |
| **CWE** | {{CWE_2}} |
| **CVSS Base** | {{CVSS_2}} |

**Deskripsi:**

{{DESKRIPSI_TEMUAN_2}}

**Bukti:**
```http
{{BUKTI_TEKNIS_2}}
```

**Dampak:**

{{DAMPAK_TEMUAN_2}}

**Rekomendasi:**
{{REKOMENDASI_TEMUAN_2}}

---

<!-- Lanjutkan T-03, T-04, dst. sesuai jumlah temuan -->

---

## 6. Matriks Risiko

| ID | Temuan | Severity | Kemudahan Eksploit | Dampak Bisnis | Prioritas |
|---|---|---|---|---|---|
| T-01 | {{JUDUL_1}} | {{SEV_ICON_1}} {{SEV_1}} | {{KEMUDAHAN_1}} | {{DAMPAK_BISNIS_1}} | **P{{PRIO_1}}** |
| T-02 | {{JUDUL_2}} | {{SEV_ICON_2}} {{SEV_2}} | {{KEMUDAHAN_2}} | {{DAMPAK_BISNIS_2}} | **P{{PRIO_2}}** |

<!-- Urutkan dari severity tertinggi ke terendah -->

---

## 7. Rekomendasi Prioritas

### 🔴 P1 — Segera (dalam 1 minggu)

**1. {{JUDUL_REKOMENDASI_P1_1}}**

{{DETAIL_REKOMENDASI_P1_1}}

---

### 🟡 P2 — Jangka Pendek (dalam 1 bulan)

**{{NOMOR}}. {{JUDUL_REKOMENDASI_P2_1}}**

{{DETAIL_REKOMENDASI_P2_1}}

---

### 🟢 P3 — Jangka Menengah (dalam 3 bulan)

**{{NOMOR}}. {{JUDUL_REKOMENDASI_P3_1}}**

{{DETAIL_REKOMENDASI_P3_1}}

---

## 8. Lampiran — Bukti Teknis

### A. {{JUDUL_LAMPIRAN_A}}

```http
REQUEST:
{{REQUEST_A}}

RESPONSE:
{{RESPONSE_A}}
```

### B. {{JUDUL_LAMPIRAN_B}}

```http
REQUEST:
{{REQUEST_B}}

RESPONSE:
{{RESPONSE_B}}
```

<!-- Tambahkan lampiran sesuai kebutuhan (C, D, dst.) -->

---

## Penutup

{{NARASI_PENUTUP}}

---

*Laporan ini dibuat untuk keperluan {{TUJUAN_LAPORAN}} oleh {{PEMBUAT_LAPORAN}}.*  
*Dokumen ini bersifat {{KLASIFIKASI}} — {{KETENTUAN_DISTRIBUSI}}.*
