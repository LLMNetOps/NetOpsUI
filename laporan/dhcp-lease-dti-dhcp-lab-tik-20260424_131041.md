# 📊 Laporan DHCP Lease — DTI (dhcp-lab-tik)

**Tanggal Pengambilan:** 2026-04-24 13:10:41  
**Router:** DTI (10.39.0.1)  
**Server DHCP:** dhcp-lab-tik  
**File:** `output/dhcp-lease-dti-dhcp-lab-tik-20260424_131041.txt`

---

## 1. Ringkasan Status

| Status | Jumlah | Persentase |
|---|---|---|
| **Bound** | 199 | 72.9% |
| **Waiting** | 63 | 23.1% |
| **Disabled (X)** | 11 | 4.0% |
| **Total** | **273** | 100% |

---

## 2. Distribusi Perangkat UTBK-OS

| Kategori | Jumlah |
|---|---|
| Bound + UTBK-OS | 196 |
| Bound + Other (non-UTBK) | 3 |
| Waiting + UTBK-OS | 1 |
| **Total UTBK-OS** | **197** |

> **Rasio UTBK-OS terhadap Bound:** 98.5% (196 dari 199 perangkat bound adalah UTBK-OS)

---

## 3. Distribusi Perangkat per Kelompok Lab

| Kelompok Lab | Jumlah | Keterangan |
|---|---|---|
| **lab3-XX** | ~66 | Lab 3 (paling banyak perangkat) |
| **Lab2-XX** | ~65 | Lab 2 |
| **Lab1-XX** | ~38 | Lab 1 |
| **lab4-XX** | ~22 | Lab 4 |
| **Pengawas** | 6 | Lab1/2/3/4 Pengawas |
| **H3C Switch** | 4 | sw-lab-tik, sw-lab-4, H3C-TES1/2 |
| **Access Point** | 3 | comment=ap |
| **Lainnya** | ~5 | Laptop, PC Sertifikasi, IWANTO |

---

## 4. Perangkat Bound Non-UTBK-OS (3 Perangkat)

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.39.0.238 | 94:3F:C2:87:B2:E8 | sw-lab-4-barat-belakang | sw-grl-4-lab3-barat-belakang | — |
| 10.39.0.9 | E8:F7:24:17:EC:F0 | — | sw-grl-3-tik-lab1-atas | — |
| 10.39.0.82 | 28:C9:7A:FC:5C:63 | sw-Lab4-selatan | H3C-fc5c63 | 3d21h |

> Perangkat non-UTBK adalah **switch infrastructure** (H3C & Mikrotik switch).

---

## 5. ⚠️ ANOMALI TERDETEKSI

### 🔴 ANOMALI 1: Perangkat Waiting Sudah Berhari-hari (CRITICAL)

Terdapat **3 perangkat waiting** yang sudah mencoba mendapatkan IP selama **3–4 hari** tetapi belum berhasil. Ini sangat tidak normal karena biasanya waiting hanya beberapa detik/menit sebelum bound atau timeout.

| # | IP Address | Comment | Hostname | Age | Last Seen |
|---|---|---|---|---|---|
| 1 | **10.39.0.80** | — | **iwanto** | **4d3h38m** | 3d21h lalu |
| 2 | **10.39.1.15** | Lab1-39 | **utbk-os** | **4d3h4m** | 21h48m lalu |
| 3 | **10.39.0.83** | — | **LAPTOP-JOFARS49** | **3d7h37m** | 3d7h lalu |

**Analisa:**
- `iwanto` (10.39.0.80) — perangkat pribadi? Sudah 4 hari mencoba DHCP tanpa sukses
- `Lab1-39` (10.39.1.15) — perangkat **UTBK-OS resmi** yang stuck di waiting selama 4 hari. **Ini anomali serius** karena perangkat sertifikasi tidak seharusnya tidak mendapat IP
- `LAPTOP-JOFARS49` (10.39.0.83) — laptop pribadi, bukan perangkat lab resmi

**Rekomendasi:**
- Cek koneksi fisik dan konfigurasi DHCP client pada ketiga perangkat
- Khusus `Lab1-39`, segera investigasi karena ini perangkat sertifikasi UTBK
- Jika tidak digunakan, disable entri untuk bebaskan slot IP

---

### 🔴 ANOMALI 2: Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu (HIGH)

Terdapat **3 perangkat waiting** yang `last-seen` sudah lebih dari **2 minggu**. Perangkat ini sudah tidak aktif di jaringan tetapi entri DHCP masih tersisa.

| # | IP Address | Comment | Hostname | Last Seen |
|---|---|---|---|---|
| 1 | **10.39.0.42** | sw-lab-tik-1-2-barat | H3C-fc582b | **2w4d4h** lalu |
| 2 | **10.39.0.7** | — | — | **2w2d** lalu |
| 3 | **10.39.0.236** | — | — | **2w2d** lalu |

**Analisa:**
- `sw-lab-tik-1-2-barat` — switch H3C yang sudah 2 minggu tidak terlihat
- `10.39.0.7` dan `10.39.0.236` — perangkat tidak dikenal, sudah 2 minggu tidak aktif

**Rekomendasi:**
- Disable/hapus entri ini untuk bebaskan IP pool
- Cek apakah switch H3C masih terpasang di lab

---

### 🟡 ANOMALI 3: Perangkat Bound Terlalu Lama (> 4 Hari)

Sebagian besar perangkat bound memiliki `age` sekitar **1–2 hari** (sesuai jadwal lab). Namun terdapat perangkat yang sudah bound lebih dari 4 hari:

| # | IP Address | Comment | Hostname | Age | Expires After |
|---|---|---|---|---|---|
| 1 | **10.39.0.68** | lab4-22 | utbk-os | **4d4h16m** | 1h41m |
| 2 | **10.39.0.82** | sw-Lab4-selatan | H3C-fc5c63 | **3d21h** | 2h31m |

**Analisa:**
- `lab4-22` (10.39.0.68) — perangkat UTBK-OS resmi yang sudah 4 hari bound. Kemungkinan perangkat tidak pernah dimatikan/dilepas dari lab
- `sw-Lab4-selatan` (10.39.0.82) — switch H3C yang bound 3 hari (wajar untuk infrastructure)

**Rekomendasi:**
- Verifikasi apakah `lab4-22` masih digunakan. Jika tidak, release lease-nya

---

### 🟡 ANOMALI 4: IP Pool Terblokir oleh Waiting Entries

**63 entri waiting** memblokir IP yang seharusnya bisa digunakan. Distribusi IP terblokir:

| Range IP | Jumlah Waiting |
|---|---|
| 10.39.0.190 – 10.39.0.212 | 15 IP |
| 10.39.0.215 – 10.39.0.230 | 16 IP |
| 10.39.1.x | 18 IP |
| Lainnya | 14 IP |

**Total IP terblokir:** 63 dari total pool (sekitar **18–20%** IP tidak tersedia)

**Rekomendasi:**
- Gunakan `reset number` di MikroTik untuk membersihkan semua entri waiting sekaligus
- Pertimbangkan mengurangi DHCP lease time untuk waiting entries

---

### 🟡 ANOMALI 5: Entri Disabled IP-nya Masih Tersisa di Pool

**11 entri disabled** masih memakan slot IP di pool DHCP:

| # | IP Address | MAC Address | Comment |
|---|---|---|---|
| 1 | 10.39.0.216 | C8:5A:CF:3C:30:CE | — |
| 2 | 10.39.0.217 | C8:5A:CF:3C:C7:02 | — |
| 3 | 10.39.0.218 | C8:5A:CF:3A:45:70 | — |
| 4 | 10.39.0.220 | C8:5A:CF:3C:11:D0 | — |
| 5 | 10.39.0.219 | C8:5A:CF:3C:31:EA | — |
| 6 | 10.39.0.221 | C8:5A:CF:3B:CC:E2 | — |
| 7 | 10.39.0.223 | C8:5A:CF:3C:E1:9C | — |
| 8 | 10.39.0.229 | C8:5A:CF:3C:83:F3 | — |
| 9 | 10.39.0.215 | C8:5A:CF:38:F6:82 | — |
| 10 | 10.39.0.222 | C8:5A:CF:3C:60:69 | — |
| 11 | 10.39.0.42 | 28:C9:7A:FC:58:2B | sw-lab-tik-1-2-barat |

> Semua MAC `C8:5A:CF:3C:XX:XX` kemungkinan perangkat **Lab 2** yang sudah tidak digunakan.

**Rekomendasi:**
- Gunakan `remove` (bukan hanya disable) untuk entri yang sudah tidak diperlukan
- Gunakan command MikroTik: `/ip dhcp-server lease remove [find where status=disabled]`

---

### 🟢 ANOMALI 6: Perangkat Bound Tanpa Comment

Hanya **1 perangkat bound** yang tidak memiliki `comment=` (selain switch infrastructure):

| IP Address | MAC Address | Hostname |
|---|---|---|
| 10.39.0.9 | E8:F7:24:17:EC:F0 | sw-grl-3-tik-lab1-atas |

> Ini adalah switch Mikrotik (`sw-grl-*`), jadi wajar tidak ada comment lab.

---

## 6. Lease Time Bound

| Metric | Nilai |
|---|---|
| **Terpendek** | 1h30m12s |
| **Terpanjang** | 2h59m7s |
| **Rata-rata** | ~2h15m |

> Lease time bervariasi antara 1h30m – 3h, menunjukkan beberapa perangkat menggunakan lease time berbeda (mungkin ada static lease atau pool berbeda).

---

## 7. Distribusi Subnet

| Subnet | Jumlah Bound | Keterangan |
|---|---|---|
| **10.39.0.x** | ~140 | Subnet utama (Lab 1, 2, 3, 4) |
| **10.39.1.x** | ~59 | Subnet tambahan (Lab 3, 4, pengawas) |

---

## 8. 📋 Ringkasan Rekomendasi

### 🔴 Prioritas Tinggi (Selesai Sekarang)
| # | Aksi | Dampak |
|---|---|---|
| 1 | **Investigasi Lab1-39 (10.39.1.15)** — perangkat UTBK-OS stuck waiting 4 hari | Perangkat sertifikasi tidak bisa akses jaringan |
| 2 | **Bersihkan 63 entri waiting** — gunakan `reset number` di MikroTik | Bebaskan ~63 slot IP pool |
| 3 | **Hapus 3 waiting entries lama** (iwanto, LAPTOP-JOFARS49, Lab1-39) | Bebaskan 3 IP yang terblokir >3 hari |

### 🟡 Prioritas Sedang (Selesai Minggu Ini)
| # | Aksi | Dampak |
|---|---|---|
| 4 | **Remove 11 entri disabled** — gunakan `remove` bukan hanya disable | Bebaskan 11 slot IP |
| 5 | **Cek switch H3C** (10.39.0.42, 10.39.0.7, 10.39.0.236) — sudah 2 minggu tidak terlihat | Verifikasi infrastruktur |
| 6 | **Verifikasi lab4-22** (10.39.0.68) — bound 4 hari, kemungkinan tidak digunakan | Hemat IP pool |

### 🟢 Prioritas Rendah (Maintenance Rutin)
| # | Aksi | Dampak |
|---|---|---|
| 7 | **Audit comment pada entri bound** — pastikan semua perangkat lab punya comment | Kemudahan tracking |
| 8 | **Blokir perangkat pribadi** (iwanto, LAPTOP-JOFARS49) di level switch/AP | Mencegah akses tidak sah |

---

*Report generated: 2026-04-24*
