# 📊 Laporan DHCP Lease — 22 April 2026

**Tanggal:** 22 April 2026
**Total Server:** 23
**File Sumber:** 23 file di direktori `output/`
**Perbandingan:** 1819 perangkat hari ini vs 1834 perangkat hari sebelumnya

---

## 🗒️ Ringkasan Eksekutif

Terdapat pergeseran signifikan pada status `lease` di mana jumlah perangkat `bound` menurun drastis sementara `waiting` meningkat tajam, mengindikasikan potensi masalah pada `DHCP server` atau konektivitas `router`. Mayoritas perangkat `bound` saat ini berasal dari segmen UTBK-OS, namun adanya 91 perangkat dengan anomali tingkat CRITICAL dan HIGH memerlukan investigasi segera untuk mencegah gangguan layanan. Tidak ada subnet yang mencapai batas kritis, namun lonjakan status `waiting` yang masif menunjukkan bahwa `pool` IP mungkin tidak lagi mampu melayani permintaan secara efisien atau ada gangguan proses `lease` renewal. Disarankan untuk segera melakukan audit pada `MAC address` yang mengalami anomali dan mengevaluasi konfigurasi `subnet` untuk memastikan stabilitas distribusi `IP address` di masa depan.

---

## 1. Ringkasan Status

Rasio `waiting` mencapai 52.8%, jauh melampaui batas normal di bawah 10%, yang mengindikasikan masalah signifikan pada proses alokasi `IP address`. Dengan `disabled` berada di 0, tidak ada perangkat yang secara manual dimatikan, sehingga anomali ini kemungkinan besar disebabkan oleh masalah pada `DHCP server` atau `router`. Diperlukan investigasi segera untuk memastikan ketersediaan `pool` dalam `subnet` dan stabilitas layanan.

| Status | Jumlah | Persentase |
|---|---|---|
| **Bound** | 858 | 47.2% |
| **Waiting** | 961 | 52.8% |
| **Disabled (X)** | 0 | 0.0% |
| **Total** | **1819** | 100% |

## 2. 📈 Tren Historis (7 Hari Terakhir)

Tren `bound` menunjukkan penurunan tajam yang mengindikasikan pelepasan massal `IP address` dari `subnet`. Sebaliknya, lonjakan `waiting` yang signifikan menandakan adanya antrian besar klien yang `waiting` `lease` baru, kemungkinan akibat `DHCP server` yang mengalami gangguan atau `pool` yang hampir habis.

| Tanggal | Bound | Waiting | Total |
|---|---|---|---|
| 21 April 2026 | 1666 | 168 | 1834 |
| 22 April 2026 | 858 | 961 | 1819 |

## 3. 📊 Utilisasi IP Pool

Dengan total 24 `subnet` yang tersedia dan tidak ada yang masuk kategori kritis atau waspada, risiko kekurangan `IP address` saat ini sangat minim. Utilisasi `IP pool` secara keseluruhan masih berada dalam batas aman, sehingga tidak ada tindakan ekspansi atau penyesuaian `pool` yang mendesak diperlukan. Fokus dapat dialihkan ke pemantauan rutin untuk memastikan tren pertumbuhan perangkat tetap terkendali.

| Subnet | Used | Total (/24) | Usage % | Status |
|---|---|---|---|---|
| 10.39.1.0/24 | 174 | 254 | 68.5% | 🟢 Normal |
| 10.27.60.0/24 | 173 | 254 | 68.1% | 🟢 Normal |
| 10.27.57.0/24 | 143 | 254 | 56.3% | 🟢 Normal |
| 10.22.13.0/24 | 134 | 254 | 52.8% | 🟢 Normal |
| 10.39.0.0/24 | 117 | 254 | 46.1% | 🟢 Normal |
| 10.27.59.0/24 | 114 | 254 | 44.9% | 🟢 Normal |
| 10.34.13.0/24 | 104 | 254 | 40.9% | 🟢 Normal |
| 10.23.82.0/24 | 94 | 254 | 37.0% | 🟢 Normal |
| 10.27.58.0/24 | 84 | 254 | 33.1% | 🟢 Normal |
| 10.36.16.0/24 | 84 | 254 | 33.1% | 🟢 Normal |
| 10.24.8.0/24 | 82 | 254 | 32.3% | 🟢 Normal |
| 10.21.192.0/24 | 68 | 254 | 26.8% | 🟢 Normal |
| 10.30.90.0/24 | 59 | 254 | 23.2% | 🟢 Normal |
| 10.28.160.0/24 | 58 | 254 | 22.8% | 🟢 Normal |
| 10.26.97.0/24 | 57 | 254 | 22.4% | 🟢 Normal |
| 10.31.16.0/24 | 53 | 254 | 20.9% | 🟢 Normal |
| 10.35.80.0/24 | 52 | 254 | 20.5% | 🟢 Normal |
| 10.23.80.0/24 | 40 | 254 | 15.7% | 🟢 Normal |
| 10.32.8.0/24 | 39 | 254 | 15.4% | 🟢 Normal |
| 10.26.121.0/24 | 29 | 254 | 11.4% | 🟢 Normal |
| 10.34.14.0/24 | 26 | 254 | 10.2% | 🟢 Normal |
| 10.25.80.0/24 | 23 | 254 | 9.1% | 🟢 Normal |
| 10.32.9.0/24 | 9 | 254 | 3.5% | 🟢 Normal |
| 10.35.81.0/24 | 3 | 254 | 1.2% | 🟢 Normal |

## 4. Distribusi Perangkat UTBK-OS

| Kategori | Jumlah |
|---|---|
| Bound + UTBK-OS | 746 |
| Bound + Other (non-UTBK) | 112 |
| **Total UTBK-OS** | **746** |

> **Rasio UTBK-OS terhadap Bound:** 86.9% (746 dari 858 perangkat bound adalah UTBK-OS)

## 5. Ringkasan per Server DHCP

Distribusi beban tidak merata, dengan `dti-dhcp-lab-tik` menangani sekitar 245 perangkat `waiting` yang jauh melampaui server lain, menandakan potensi bottleneck atau konfigurasi `subnet` yang perlu ditinjau. Sementara itu, server seperti `fh-lab` dan `filkom-G1.4-vlan3496` hanya mencatat nol perangkat `waiting`, menunjukkan utilisasi yang sangat rendah atau potensi `disabled` pada layanan mereka. Ketimpangan ini mengindikasikan bahwa beberapa `DHCP server` kelebihan beban sementara yang lain hampir kosong, sehingga memerlukan redistribusi `pool` atau penyesuaian `lease` time untuk menyeimbangkan trafik.

| Server | Bound | Waiting | Disabled | Total | UTBK-OS | Other |
|---|---|---|---|---|---|---|
| dti-dhcp-lab-tik | 46 | 245 | 0 | 291 | 43 | 3 |
| fapet-network-Lab | 0 | 23 | 0 | 23 | 0 | 0 |
| feb-CBT | 3 | 131 | 0 | 134 | 3 | 0 |
| fh-lab | 68 | 0 | 0 | 68 | 68 | 0 |
| fia-dhcp-2380-lab | 3 | 131 | 0 | 134 | 1 | 2 |
| fib-server-lab | 2 | 46 | 0 | 48 | 0 | 2 |
| filkom-G1.2-vlan3498 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.3-vlan3495 | 1 | 25 | 0 | 26 | 1 | 0 |
| filkom-G1.4-vlan3496 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.5-vlan3499 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.6-vlan3497 | 26 | 0 | 0 | 26 | 26 | 0 |
| fisip-serverpoollab | 2 | 51 | 0 | 53 | 0 | 2 |
| fk-1-LAB_Lt.1 | 172 | 1 | 0 | 173 | 94 | 78 |
| fk-8-dhcp_LabA | 101 | 13 | 0 | 114 | 99 | 2 |
| fk-8-dhcp_LabB | 140 | 3 | 0 | 143 | 139 | 1 |
| fk-8-dhcp_LabC | 84 | 0 | 0 | 84 | 68 | 16 |
| fkg-dhcp2 | 73 | 11 | 0 | 84 | 67 | 6 |
| fp-lab | 0 | 82 | 0 | 82 | 0 | 0 |
| fpik-serverlabutbk | 1 | 57 | 0 | 58 | 1 | 0 |
| ft-dekanat-Lab-66-pimp | 0 | 57 | 0 | 57 | 0 | 0 |
| ft-gbe-Lab-67-Admin | 0 | 29 | 0 | 29 | 0 | 0 |
| ftp-dhcp7 | 58 | 1 | 0 | 59 | 58 | 0 |
| vokasi-3508-serverpoollab | 0 | 55 | 0 | 55 | 0 | 0 |

## 6. Perangkat Bound Non-UTBK-OS

### Server: dti-dhcp-lab-tik

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.39.0.238 | 94:3F:C2:87:B2:E8 | sw-lab-4-barat-belakang | sw-grl-4-lab3-barat-belakang | - |
| 10.39.0.9 | E8:F7:24:17:EC:F0 | - | sw-grl-3-tik-lab1-atas | - |
| 10.39.0.82 | 28:C9:7A:FC:5C:63 | sw-lab4-selatan | H3C-fc5c63 | 2d1h53m43s |

### Server: fia-dhcp-2380-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.23.82.32 | 30:9C:23:C1:62:17 | - | DESKTOP-UTR5SS5 | - |
| 10.23.82.110 | 8C:85:C1:B5:A9:CE | - | - | - |

### Server: fib-server-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.32.8.150 | EC:9B:8B:78:4B:8E | sw-lab-1 | HPE | - |
| 10.32.8.151 | EC:9B:8B:78:49:5E | sw-lab-2 | HPE | - |

### Server: fisip-serverpoollab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.31.16.54 | D4:93:90:18:C3:6B | laptop | utbk-pc-disabilitas02 | 22w5d8h2m15s |
| 10.31.16.53 | D4:93:90:18:D1:A7 | laptop | utbk-pc-disabilitas01 | 22w5d7h35m35s |

### Server: fk-1-LAB_Lt.1

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.60.140 | 14:CB:19:0C:B8:1F | - | debian | - |
| 10.27.60.144 | E4:E7:49:51:FB:36 | - | UB-C-WS281 | - |
| 10.27.60.181 | 14:CB:19:0C:68:55 | - | - | - |
| 10.27.60.180 | 14:CB:19:0C:08:98 | - | - | - |
| 10.27.60.141 | 14:CB:19:0C:68:D6 | - | - | - |
| 10.27.60.186 | 14:CB:19:0C:37:3D | - | - | - |
| 10.27.60.143 | 14:CB:19:0C:D6:5B | - | UB-A-WS065 | - |
| 10.27.60.193 | 14:CB:19:0C:37:43 | - | - | - |
| 10.27.60.179 | 14:CB:19:0C:D7:E7 | - | debian | - |
| 10.27.60.111 | 14:CB:19:0C:D3:81 | - | - | - |
| 10.27.60.127 | 14:CB:19:0C:67:0C | - | - | - |
| 10.27.60.188 | 14:CB:19:0C:A8:CE | - | - | - |
| 10.27.60.191 | 14:CB:19:0C:77:8F | - | - | - |
| 10.27.60.115 | 14:CB:19:0C:37:2A | - | - | - |
| 10.27.60.126 | 14:CB:19:0C:C7:12 | - | - | - |
| 10.27.60.182 | 14:CB:19:0C:68:0B | - | debian | - |
| 10.27.60.142 | 14:CB:19:0C:D3:48 | - | - | - |
| 10.27.60.189 | 14:CB:19:0C:17:69 | - | - | - |
| 10.27.60.123 | 14:CB:19:0C:47:A6 | - | - | - |
| 10.27.60.145 | E4:E7:49:51:FB:FE | - | debian | - |
| 10.27.60.190 | 14:CB:19:0C:B6:9A | - | - | - |
| 10.27.60.112 | 14:CB:19:0C:27:13 | - | - | - |
| 10.27.60.109 | E4:E7:49:51:F7:0D | - | UB-C-WS281 | - |
| 10.27.60.146 | E4:E7:49:51:F1:48 | - | UB-C-WS281 | - |
| 10.27.60.163 | E4:E7:49:51:F9:17 | - | - | - |
| 10.27.60.167 | E4:E7:49:51:F9:8E | - | UB-C-WS281 | - |
| 10.27.60.187 | 14:CB:19:0C:A8:B2 | - | UB-A-WS065 | - |
| 10.27.60.177 | 14:CB:19:0B:CB:8E | - | - | - |
| 10.27.60.122 | 14:CB:19:0C:58:1E | - | UB-A-WS065 | - |
| 10.27.60.166 | E4:E7:49:51:FA:54 | - | - | - |
| 10.27.60.105 | E4:E7:49:51:F6:04 | - | debian | - |
| 10.27.60.152 | E4:E7:49:51:F5:BB | - | UB-C-WS281 | - |
| 10.27.60.118 | 14:CB:19:0C:38:5B | - | UB-A-WS065 | - |
| 10.27.60.113 | 14:CB:19:0C:47:57 | - | UB-A-WS065 | - |
| 10.27.60.161 | E4:E7:49:51:FB:F9 | - | UB-C-WS281 | - |
| 10.27.60.131 | E4:E7:49:51:F9:0C | - | - | - |
| 10.27.60.98 | E4:E7:49:51:F7:63 | - | UB-C-WS281 | - |
| 10.27.60.153 | E4:E7:49:51:F7:C9 | - | UB-C-WS281 | - |
| 10.27.60.99 | E4:E7:49:51:FB:3F | - | - | - |
| 10.27.60.151 | E4:E7:49:51:F9:F8 | - | debian | - |
| 10.27.60.103 | E4:E7:49:51:FA:16 | - | - | - |
| 10.27.60.168 | E4:E7:49:51:FA:0C | - | debian | - |
| 10.27.60.154 | E4:E7:49:51:FC:01 | - | UB-C-WS281 | - |
| 10.27.60.104 | E4:E7:49:51:F8:5C | - | - | - |
| 10.27.60.137 | E4:E7:49:51:FB:85 | - | UB-C-WS281 | - |
| 10.27.60.101 | E4:E7:49:51:F5:F7 | - | UB-C-WS281 | - |
| 10.27.60.150 | E4:E7:49:51:FB:F6 | - | UB-C-WS281 | - |
| 10.27.60.206 | 14:CB:19:0C:18:77 | - | - | - |
| 10.27.60.240 | 14:CB:19:0C:82:B7 | - | debian | - |
| 10.27.60.247 | 14:CB:19:0B:EB:20 | - | UB-A-WS065 | - |
| 10.27.60.230 | 14:CB:19:0C:24:28 | - | UB-A-WS065 | - |
| 10.27.60.249 | 14:CB:19:0B:DB:70 | - | UB-A-WS065 | - |
| 10.27.60.136 | 14:CB:19:0C:57:3E | - | UB-A-WS065 | - |
| 10.27.60.95 | 14:CB:19:0C:18:58 | - | - | - |
| 10.27.60.133 | 14:CB:19:0C:38:B9 | - | - | - |
| 10.27.60.210 | 14:CB:19:0B:FB:59 | - | debian | - |
| 10.27.60.201 | 14:CB:19:0C:77:FC | - | - | - |
| 10.27.60.207 | 14:CB:19:0C:08:B8 | - | debian | - |
| 10.27.60.199 | 14:CB:19:0B:EB:5C | - | - | - |
| 10.27.60.208 | 14:CB:19:0C:08:E6 | - | - | - |
| 10.27.60.204 | 14:CB:19:0C:A8:C4 | - | - | - |
| 10.27.60.215 | 14:CB:19:0C:34:52 | - | UB-A-WS065 | - |
| 10.27.60.202 | 14:CB:19:0C:08:3D | - | - | - |
| 10.27.60.213 | 14:CB:19:0C:38:6B | - | UB-A-WS065 | - |
| 10.27.60.211 | 14:CB:19:0C:48:53 | - | UB-A-WS065 | - |
| 10.27.60.203 | 14:CB:19:0C:28:4D | - | - | - |
| 10.27.60.198 | 14:CB:19:0C:28:41 | - | - | - |
| 10.27.60.159 | E4:E7:49:51:F6:FB | - | UB-C-WS281 | - |
| 10.27.60.158 | E4:E7:49:51:F8:B5 | - | UB-C-WS281 | - |
| 10.27.60.165 | E4:E7:49:51:FC:14 | - | debian | - |
| 10.27.60.170 | E4:E7:49:51:FB:28 | - | - | - |
| 10.27.60.172 | E4:E7:49:51:F5:B5 | - | - | - |
| 10.27.60.174 | E4:E7:49:51:F8:75 | - | debian | - |
| 10.27.60.89 | E4:E7:49:51:F8:F0 | 162 | UB-D-WS162 | - |
| 10.27.60.87 | E4:E7:49:51:F9:A6 | 121 | debian | - |
| 10.27.60.82 | E4:E7:49:51:FA:F7 | 168 | UB-D-WS162 | - |
| 10.27.60.74 | 10:FF:E0:66:70:82 | - | pxeutbk | 6d7h39m24s |
| 10.27.60.76 | 14:CB:19:0C:57:C3 | - | - | 5d1h5m16s |

### Server: fk-8-dhcp_LabA

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.59.50 | D4:61:37:0D:09:28 | - | - | - |
| 10.27.59.107 | D4:61:37:0C:C5:B7 | - | - | - |

### Server: fk-8-dhcp_LabB

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.57.42 | EC:8E:B5:D7:AA:C9 | - | UB-B-WS178 | - |

### Server: fk-8-dhcp_LabC

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.58.187 | D0:50:99:72:B8:47 | - | UB-D-WS353 | - |
| 10.27.58.39 | D0:50:99:72:B7:72 | - | UB-D-WS354 | - |
| 10.27.58.54 | E0:69:95:DD:30:85 | - | UB-D-WS352 | - |
| 10.27.58.127 | 00:FD:45:18:02:40 | - | - | - |
| 10.27.58.34 | D0:50:99:75:61:0C | - | UB-D-WS355 | - |
| 10.27.58.133 | D0:50:99:75:60:8D | - | - | - |
| 10.27.58.47 | E0:69:95:DD:32:6E | - | UB-D-WS345 | - |
| 10.27.58.43 | E0:69:95:DD:5F:AC | - | UB-D-WS351 | - |
| 10.27.58.37 | E0:69:95:DD:3A:0A | - | UB-D-WS344 | - |
| 10.27.58.50 | E0:69:95:DD:28:D9 | - | UB-D-WS343 | - |
| 10.27.58.36 | 40:B0:34:28:A9:4B | - | UB-B-WS140 | - |
| 10.27.58.46 | EC:8E:B5:D7:AA:78 | - | UB-D-WS348 | - |
| 10.27.58.48 | EC:8E:B5:D7:AA:CE | - | UB-D-WS349 | - |
| 10.27.58.51 | 40:B0:34:28:A9:15 | - | UB-D-WS347 | - |
| 10.27.58.186 | D0:50:99:72:B8:18 | - | - | - |
| 10.27.58.38 | 04:7C:16:1C:83:67 | - | pxe-utbk-C | - |

### Server: fkg-dhcp2

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.36.16.204 | 20:FD:F1:1E:E3:DE | - | sw-fkg-c-4 | - |
| 10.36.16.74 | 40:01:C6:BA:24:00 | - | sw-fkg-c-3 | - |
| 10.36.16.72 | 40:01:C6:E6:3A:F2 | - | sw-fkg-c-5 | - |
| 10.36.16.117 | A4:0E:75:34:3E:20 | - | sw-fkg-c-x-1 | - |
| 10.36.16.41 | A4:0E:75:34:47:60 | - | sw-fkg-c-x-2 | - |
| 10.36.16.177 | E0:D5:5E:16:50:4D | - | DESKTOP-36KP9AD | - |

> Perangkat non-UTBK adalah **switch infrastructure** dan perangkat lainnya.

## 7. 📡 Perangkat Baru & Disconnect

Terdeteksi 3 perangkat baru yang masuk ke jaringan, sementara 19 perangkat mengalami `disconnect`. Jumlah `disconnect` yang signifikan ini perlu diinvestigasi lebih lanjut untuk memastikan apakah ada masalah pada `DHCP server`, `lease` yang kadaluarsa, atau potensi pergerakan perangkat yang tidak wajar di dalam `subnet`.

### 🔵 Perangkat Baru Terdeteksi (3 perangkat)

Perangkat yang **pertama kali terlihat** pada tanggal ini (berdasarkan MAC address).

| MAC Address | IP Address | Comment | Hostname | Client ID | Status | Server |
|---|---|---|---|---|---|---|
| D4:93:90:18:C3:6B | 10.31.16.54 | laptop | utbk-pc-disabilitas02 | 1:d4:93:90:18:c3:6b | bound | fisip-serverpoollab |
| D4:93:90:18:D1:A7 | 10.31.16.53 | laptop | utbk-pc-disabilitas01 | 1:d4:93:90:18:d1:a7 | bound | fisip-serverpoollab |
| E4:E7:49:51:FC:23 | 10.28.160.179 | - | utbk-os | 1:e4:e7:49:51:fc:23 | waiting | fpik-serverlabutbk |

### 🔴 Perangkat Disconnect (19 perangkat)

Perangkat yang **tidak terlihat** pada tanggal ini tetapi pernah ada di hari sebelumnya.

| MAC Address | Terakhir Seen | Server Terakhir |
|---|---|---|
| 08:8F:C3:BE:4C:D4 | 20260421 | fisip-serverpoollab |
| 08:8F:C3:BE:4F:D9 | 20260421 | fisip-serverpoollab |
| 20:3A:43:02:65:F1 | 20260421 | fia-dhcp-2380-lab |
| 34:5A:60:44:FD:2D | 20260421 | fk-8-dhcp_LabA |
| 8C:32:23:32:30:31 | 20260421 | fia-dhcp-2380-lab |
| D4:61:37:0C:C1:B3 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:C4:D9 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:C5:BE | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:C6:39 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:C6:3D | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:CD:65 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:CE:84 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:CF:53 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:CF:70 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0C:CF:C7 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0D:07:9C | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0D:07:C2 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0D:08:98 | 20260421 | fk-8-dhcp_LabA |
| D4:61:37:0D:08:BC | 20260421 | fk-8-dhcp_LabA |

---

## 8. 📍 Anomali per Router

Distribusi anomali tersebar merata pada lima `router` dengan satu kasus per perangkat, sehingga tidak ada `router` tunggal yang mendominasi volume error. Namun, `fia-dhcp-2380-lab` harus menjadi prioritas penanganan pertama karena label `CRITICAL` mengindikasikan risiko gangguan layanan yang lebih serius dibandingkan kasus `HIGH` dan `MEDIUM` pada `router` lainnya.

### dti-dhcp-lab-tik (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w2d8h58m27s |
| 🔴 HIGH | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w2d8h58m27s |

### fia-dhcp-2380-lab (32 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.23.80.6 | DESKTOP-C75KJDC | fia-dhcp-2380-lab | Waiting: 20w6d4h18m25s |
| 🔴 CRITICAL | 10.23.80.44 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h44m40s |
| 🔴 CRITICAL | 10.23.80.36 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h40m17s |
| 🔴 CRITICAL | 10.23.80.38 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h40m11s |
| 🔴 CRITICAL | 10.23.80.40 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h40m1s |
| 🔴 CRITICAL | 10.23.80.42 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h39m54s |
| 🔴 CRITICAL | 10.23.80.39 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h5m51s |
| 🔴 CRITICAL | 10.23.80.34 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m58s |
| 🔴 CRITICAL | 10.23.80.31 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m51s |
| 🔴 CRITICAL | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m50s |
| 🔴 CRITICAL | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m47s |
| 🔴 CRITICAL | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m25s |
| 🔴 CRITICAL | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d3h27m3s |
| 🔴 CRITICAL | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d3h23m33s |
| 🔴 CRITICAL | 10.23.80.27 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w1d7h18m44s |
| 🔴 CRITICAL | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 17w6d5h30m40s |
| 🔴 HIGH | 10.23.80.6 | DESKTOP-C75KJDC | fia-dhcp-2380-lab | Waiting: 20w6d4h18m25s |
| 🔴 HIGH | 10.23.80.44 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h44m40s |
| 🔴 HIGH | 10.23.80.36 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h40m17s |
| 🔴 HIGH | 10.23.80.38 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h40m11s |
| 🔴 HIGH | 10.23.80.40 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h40m1s |
| 🔴 HIGH | 10.23.80.42 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h39m54s |
| 🔴 HIGH | 10.23.80.39 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d8h5m51s |
| 🔴 HIGH | 10.23.80.34 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m58s |
| 🔴 HIGH | 10.23.80.31 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m51s |
| 🔴 HIGH | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m50s |
| 🔴 HIGH | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m47s |
| 🔴 HIGH | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d4h13m25s |
| 🔴 HIGH | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d3h27m3s |
| 🔴 HIGH | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w5d3h23m33s |
| 🔴 HIGH | 10.23.80.27 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w1d7h18m44s |
| 🔴 HIGH | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 17w6d5h30m40s |

### fisip-serverpoollab (53 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.31.16.47 | utbk-os | fisip-serverpoollab | Waiting: 22w5d8h9m34s |
| 🔴 CRITICAL | 10.31.16.48 | utbk-os | fisip-serverpoollab | Waiting: 22w5d8h7m40s |
| 🔴 CRITICAL | 10.31.16.50 | utbk-os | fisip-serverpoollab | Waiting: 22w5d8h6m52s |
| 🔴 CRITICAL | 10.31.16.49 | utbk-os | fisip-serverpoollab | Waiting: 22w5d8h5m56s |
| 🔴 CRITICAL | 10.31.16.52 | utbk-os | fisip-serverpoollab | Waiting: 22w5d8h5m51s |
| 🔴 CRITICAL | 10.31.16.55 | LAB-A25 | fisip-serverpoollab | Waiting: 22w5d8h2m15s |
| 🔴 CRITICAL | 10.31.16.43 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m48s |
| 🔴 CRITICAL | 10.31.16.31 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m23s |
| 🔴 CRITICAL | 10.31.16.32 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m21s |
| 🔴 CRITICAL | 10.31.16.33 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m20s |
| 🔴 CRITICAL | 10.31.16.34 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m18s |
| 🔴 CRITICAL | 10.31.16.35 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m16s |
| 🔴 CRITICAL | 10.31.16.36 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m14s |
| 🔴 CRITICAL | 10.31.16.37 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m12s |
| 🔴 CRITICAL | 10.31.16.38 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m9s |
| 🔴 CRITICAL | 10.31.16.39 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m8s |
| 🔴 CRITICAL | 10.31.16.40 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m8s |
| 🔴 CRITICAL | 10.31.16.41 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m6s |
| 🔴 CRITICAL | 10.31.16.42 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m5s |
| 🔴 CRITICAL | 10.31.16.51 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h58m3s |
| 🔴 CRITICAL | 10.31.16.56 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h57m5s |
| 🔴 CRITICAL | 10.31.16.57 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h57m2s |
| 🔴 CRITICAL | 10.31.16.58 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m57s |
| 🔴 CRITICAL | 10.31.16.60 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m55s |
| 🔴 CRITICAL | 10.31.16.61 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m53s |
| 🔴 CRITICAL | 10.31.16.59 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m53s |
| 🔴 CRITICAL | 10.31.16.67 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m50s |
| 🔴 CRITICAL | 10.31.16.62 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m49s |
| 🔴 CRITICAL | 10.31.16.63 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m47s |
| 🔴 CRITICAL | 10.31.16.66 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m46s |
| 🔴 CRITICAL | 10.31.16.65 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m45s |
| 🔴 CRITICAL | 10.31.16.64 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m43s |
| 🔴 CRITICAL | 10.31.16.69 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m42s |
| 🔴 CRITICAL | 10.31.16.72 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m41s |
| 🔴 CRITICAL | 10.31.16.70 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m40s |
| 🔴 CRITICAL | 10.31.16.73 | LAB-B18 | fisip-serverpoollab | Waiting: 22w5d7h56m38s |
| 🔴 CRITICAL | 10.31.16.71 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m37s |
| 🔴 CRITICAL | 10.31.16.77 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m35s |
| 🔴 CRITICAL | 10.31.16.76 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m33s |
| 🔴 CRITICAL | 10.31.16.78 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m32s |
| 🔴 CRITICAL | 10.31.16.75 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m31s |
| 🔴 CRITICAL | 10.31.16.74 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h56m26s |
| 🔴 CRITICAL | 10.31.16.46 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h51m38s |
| 🔴 CRITICAL | 10.31.16.45 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h51m37s |
| 🔴 CRITICAL | 10.31.16.44 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h45m57s |
| 🔴 CRITICAL | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 22w5d7h44m35s |
| 🔴 CRITICAL | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 22w5d7h44m27s |
| 🔴 CRITICAL | 10.31.16.68 | utbk-os | fisip-serverpoollab | Waiting: 22w5d7h41m14s |
| 🔴 HIGH | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 9w6d5h59m56s |
| 🔴 HIGH | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 9w6d5h59m39s |
| 🔴 HIGH | 10.31.16.55 | LAB-A25 | fisip-serverpoollab | Waiting: 9w6d4h41m21s |
| 🟡 MEDIUM | 10.31.16.54 | utbk-pc-disabilitas02 | fisip-serverpoollab | Age: 22w5d8h2m15s |
| 🟡 MEDIUM | 10.31.16.53 | utbk-pc-disabilitas01 | fisip-serverpoollab | Age: 22w5d7h35m35s |

### fk-1-LAB_Lt.1 (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.27.60.176 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 31w1d2h53m3s |
| 🔴 HIGH | 10.27.60.176 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 31w1d2h53m3s |

### vokasi-3508-serverpoollab (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.35.80.83 | 555606b | vokasi-3508-serverpoollab | Waiting: 448w5d14h1m47s |
| 🔴 HIGH | 10.35.80.83 | 555606b | vokasi-3508-serverpoollab | Waiting: 448w5d14h1m47s |

## 9. ⚠️ ANOMALI TERDETEKSI

67 perangkat dengan status `waiting` selama berhari-hari menunjukkan kegagalan `lease` yang masif dan kritis, sementara 22 entri yang tidak terlihat lebih dari dua minggu kemungkinan besar sudah tidak aktif dan harus segera di-`disabled` untuk membebaskan slot di `IP pool`. Meskipun hanya ada 2 kasus `bound` yang melebihi batas 3 hari, durasi `waiting` terlama mencapai hampir 10 minggu mengindikasikan masalah infrastruktur atau konfigurasi `DHCP server` yang perlu segera ditangani untuk mencegah kehabisan alamat `IP address` di `subnet` tersebut.

### 🔴 ANOMALI 1: Perangkat Waiting Sudah Berhari-hari (CRITICAL)

Terdapat **67 perangkat waiting** yang sudah mencoba mendapatkan IP selama lebih dari 1 hari.

| IP | Comment | Hostname | MAC | Durasi |
|---|---|---|---|---|
| 10.35.80.83 | BACKUP | 555606b | 78:45:C4:07:9E:E9 | 448w5d14h1m47s |
| 10.27.60.176 | - | UB-C-WS281 | E4:E7:49:51:FB:E6 | 31w1d2h53m3s |
| 10.31.16.47 | - | utbk-os | 08:8F:C3:BE:4E:D4 | 22w5d8h9m34s |
| 10.31.16.48 | - | utbk-os | 08:8F:C3:BE:4C:A5 | 22w5d8h7m40s |
| 10.31.16.50 | - | utbk-os | 08:8F:C3:BE:4F:1B | 22w5d8h6m52s |
| 10.31.16.49 | - | utbk-os | 08:8F:C3:BE:4F:EE | 22w5d8h5m56s |
| 10.31.16.52 | - | utbk-os | 08:8F:C3:BE:50:06 | 22w5d8h5m51s |
| 10.31.16.55 | - | LAB-A25 | 08:8F:C3:BE:4E:4D | 22w5d8h2m15s |
| 10.31.16.43 | - | utbk-os | 08:8F:C3:BE:4C:ED | 22w5d7h58m48s |
| 10.31.16.31 | - | utbk-os | 08:8F:C3:BE:4D:8E | 22w5d7h58m23s |
| 10.31.16.32 | - | utbk-os | 08:8F:C3:BE:4F:26 | 22w5d7h58m21s |
| 10.31.16.33 | - | utbk-os | 08:8F:C3:BE:51:F3 | 22w5d7h58m20s |
| 10.31.16.34 | - | utbk-os | 08:8F:C3:BE:4F:C5 | 22w5d7h58m18s |
| 10.31.16.35 | - | utbk-os | 08:8F:C3:BE:4F:A0 | 22w5d7h58m16s |
| 10.31.16.36 | - | utbk-os | 08:8F:C3:BE:4F:7A | 22w5d7h58m14s |
| 10.31.16.37 | - | utbk-os | 08:8F:C3:BE:4F:D4 | 22w5d7h58m12s |
| 10.31.16.38 | - | utbk-os | 08:8F:C3:BE:4C:26 | 22w5d7h58m9s |
| 10.31.16.39 | - | utbk-os | 08:8F:C3:BE:4F:BC | 22w5d7h58m8s |
| 10.31.16.40 | - | utbk-os | 08:8F:C3:BE:4E:FA | 22w5d7h58m8s |
| 10.31.16.41 | - | utbk-os | 08:8F:C3:BE:4F:89 | 22w5d7h58m6s |
| 10.31.16.42 | - | utbk-os | 08:8F:C3:BE:4E:F6 | 22w5d7h58m5s |
| 10.31.16.51 | - | utbk-os | 08:8F:C3:BE:4F:52 | 22w5d7h58m3s |
| 10.31.16.56 | - | utbk-os | 08:8F:C3:BE:4D:24 | 22w5d7h57m5s |
| 10.31.16.57 | - | utbk-os | 08:8F:C3:BD:E4:DC | 22w5d7h57m2s |
| 10.31.16.58 | - | utbk-os | 08:8F:C3:BE:4F:BE | 22w5d7h56m57s |
| 10.31.16.60 | - | utbk-os | 08:8F:C3:BE:4C:EC | 22w5d7h56m55s |
| 10.31.16.61 | - | utbk-os | 08:8F:C3:BE:4F:A1 | 22w5d7h56m53s |
| 10.31.16.59 | - | utbk-os | 08:8F:C3:BE:50:BB | 22w5d7h56m53s |
| 10.31.16.67 | - | utbk-os | 08:8F:C3:BE:4F:D8 | 22w5d7h56m50s |
| 10.31.16.62 | - | utbk-os | 08:8F:C3:BE:4D:A2 | 22w5d7h56m49s |
| 10.31.16.63 | - | utbk-os | 08:8F:C3:BE:4F:BD | 22w5d7h56m47s |
| 10.31.16.66 | - | utbk-os | 08:8F:C3:BE:4F:B8 | 22w5d7h56m46s |
| 10.31.16.65 | - | utbk-os | 08:8F:C3:BE:51:F2 | 22w5d7h56m45s |
| 10.31.16.64 | - | utbk-os | 08:8F:C3:BE:4F:95 | 22w5d7h56m43s |
| 10.31.16.69 | - | utbk-os | 08:8F:C3:BE:4D:1B | 22w5d7h56m42s |
| 10.31.16.72 | - | utbk-os | 08:8F:C3:BE:4B:23 | 22w5d7h56m41s |
| 10.31.16.70 | - | utbk-os | 08:8F:C3:BE:4F:7B | 22w5d7h56m40s |
| 10.31.16.73 | - | LAB-B18 | 08:8F:C3:BC:10:C8 | 22w5d7h56m38s |
| 10.31.16.71 | - | utbk-os | 08:8F:C3:BE:4E:C1 | 22w5d7h56m37s |
| 10.31.16.77 | - | utbk-os | 08:8F:C3:BE:4C:CB | 22w5d7h56m35s |
| 10.31.16.76 | - | utbk-os | 08:8F:C3:BE:4E:C7 | 22w5d7h56m33s |
| 10.31.16.78 | - | utbk-os | 08:8F:C3:BE:4F:27 | 22w5d7h56m32s |
| 10.31.16.75 | - | utbk-os | 08:8F:C3:BE:4C:D5 | 22w5d7h56m31s |
| 10.31.16.74 | - | utbk-os | 08:8F:C3:BE:4F:01 | 22w5d7h56m26s |
| 10.31.16.46 | - | utbk-os | 08:8F:C3:BE:4E:FD | 22w5d7h51m38s |
| 10.31.16.45 | - | utbk-os | 08:8F:C3:BE:4F:6D | 22w5d7h51m37s |
| 10.31.16.44 | - | utbk-os | 08:8F:C3:BE:4F:84 | 22w5d7h45m57s |
| 10.31.16.79 | - | LAB-B24 | 08:8F:C3:BE:4F:CD | 22w5d7h44m35s |
| 10.31.16.80 | - | LAB-B25 | 08:8F:C3:BE:4F:98 | 22w5d7h44m27s |
| 10.31.16.68 | - | utbk-os | 08:8F:C3:BE:4F:B2 | 22w5d7h41m14s |
| 10.23.80.6 | LAB-UTBK-2 | DESKTOP-C75KJDC | E4:E7:49:51:FA:F8 | 20w6d4h18m25s |
| 10.23.80.44 | LAB-UTBK-40 | LAB-SIM-01 | 00:24:7E:0A:85:C1 | 19w5d8h44m40s |
| 10.23.80.36 | LAB-UTBK-32 | LAB-SIM-01 | 00:24:7E:0A:85:42 | 19w5d8h40m17s |
| 10.23.80.38 | LAB-UTBK-34 | LAB-SIM-01 | 00:24:7E:0A:84:33 | 19w5d8h40m11s |
| 10.23.80.40 | LAB-UTBK-36 | LAB-SIM-01 | 00:24:7E:0A:84:7A | 19w5d8h40m1s |
| 10.23.80.42 | LAB-UTBK-38 | LAB-SIM-01 | 00:24:7E:0A:83:EC | 19w5d8h39m54s |
| 10.23.80.39 | LAB-UTBK-35 | LAB-SIM-01 | 00:24:7E:0A:4C:42 | 19w5d8h5m51s |
| 10.23.80.34 | LAB-UTBK-30 | LAB-SIM-01 | 00:10:C6:B0:E1:26 | 19w5d4h13m58s |
| 10.23.80.31 | LAB-UTBK-27 | LAB-SIM-01 | 00:10:C6:B0:E0:92 | 19w5d4h13m51s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 70:F3:95:01:2E:40 | 19w5d4h13m50s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 00:24:7E:0A:83:CE | 19w5d4h13m47s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 00:24:7E:0A:84:0E | 19w5d4h13m25s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 00:24:7E:0A:84:04 | 19w5d3h27m3s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 00:24:7E:0A:83:E5 | 19w5d3h23m33s |
| 10.23.80.27 | LAB-UTBK-23 | LAB-SIM-01 | 00:24:7E:0A:4B:D1 | 19w1d7h18m44s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 00:24:7E:0A:84:21 | 17w6d5h30m40s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 28:C9:7A:FC:58:2B | 2w2d8h58m27s |

**Rekomendasi:** Cek koneksi fisik dan konfigurasi DHCP client. Jika tidak digunakan, disable entri.

---

### 🔴 ANOMALI 2: Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu (HIGH)

Terdapat **22 perangkat waiting** yang `last-seen` sudah lebih dari 2 minggu.

| IP | Comment | Hostname | Last Seen |
|---|---|---|---|
| 10.35.80.83 | BACKUP | 555606b | 448w5d14h1m47s |
| 10.27.60.176 | - | UB-C-WS281 | 31w1d2h53m3s |
| 10.23.80.6 | LAB-UTBK-2 | DESKTOP-C75KJDC | 20w6d4h18m25s |
| 10.23.80.44 | LAB-UTBK-40 | LAB-SIM-01 | 19w5d8h44m40s |
| 10.23.80.36 | LAB-UTBK-32 | LAB-SIM-01 | 19w5d8h40m17s |
| 10.23.80.38 | LAB-UTBK-34 | LAB-SIM-01 | 19w5d8h40m11s |
| 10.23.80.40 | LAB-UTBK-36 | LAB-SIM-01 | 19w5d8h40m1s |
| 10.23.80.42 | LAB-UTBK-38 | LAB-SIM-01 | 19w5d8h39m54s |
| 10.23.80.39 | LAB-UTBK-35 | LAB-SIM-01 | 19w5d8h5m51s |
| 10.23.80.34 | LAB-UTBK-30 | LAB-SIM-01 | 19w5d4h13m58s |
| 10.23.80.31 | LAB-UTBK-27 | LAB-SIM-01 | 19w5d4h13m51s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 19w5d4h13m50s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 19w5d4h13m47s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 19w5d4h13m25s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 19w5d3h27m3s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 19w5d3h23m33s |
| 10.23.80.27 | LAB-UTBK-23 | LAB-SIM-01 | 19w1d7h18m44s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 17w6d5h30m40s |
| 10.31.16.79 | - | LAB-B24 | 9w6d5h59m56s |
| 10.31.16.80 | - | LAB-B25 | 9w6d5h59m39s |
| 10.31.16.55 | - | LAB-A25 | 9w6d4h41m21s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 2w2d8h58m27s |

**Rekomendasi:** Disable/hapus entri ini untuk bebaskan IP pool.

---

### 🟡 ANOMALI 3: Perangkat Bound Terlalu Lama (> 3 Hari) (MEDIUM)

Terdapat **2 perangkat bound** yang sudah lebih dari 3 hari.

| IP | Comment | Hostname | Age | Expires After |
|---|---|---|---|---|
| 10.31.16.54 | laptop | utbk-pc-disabilitas02 | 22w5d8h2m15s | 39s |
| 10.31.16.53 | laptop | utbk-pc-disabilitas01 | 22w5d7h35m35s | 1m43s |

**Rekomendasi:** Verifikasi apakah perangkat masih digunakan.

---

## 10. 📋 Ringkasan Rekomendasi

### 🔴 Prioritas Tinggi
| # | Anomali | Aksi |
|---|---|---|
| 1 | Perangkat Waiting Sudah Berhari-hari | Cek koneksi fisik dan konfigurasi DHCP client. Jika tidak digunakan, disable entri. |

### 🟡 Prioritas Sedang
| # | Anomali | Aksi |
|---|---|---|
| 1 | Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu | Disable/hapus entri ini untuk bebaskan IP pool. |

### 🟢 Prioritas Rendah
| # | Anomali | Aksi |
|---|---|---|
| 1 | Perangkat Bound Terlalu Lama (> 3 Hari) | Verifikasi apakah perangkat masih digunakan. |

---

*Report generated: 22 April 2026*
