# 📊 Laporan DHCP Lease — 21 April 2026

**Tanggal:** 21 April 2026
**Total Server:** 23
**File Sumber:** 23 file di direktori `output/`

---

## 🗒️ Ringkasan Eksekutif

Harian DHCP menunjukkan dominasi status `bound` sebesar 90.8% dengan total 1666 perangkat aktif, sementara 168 perangkat lainnya masih dalam status `waiting`. Komposisi traffic sangat didominasi oleh aplikasi UTBK-OS yang mencakup 93.3% dari seluruh `lease` aktif, mengindikasikan beban kerja terpusat pada layanan tersebut. Terdapat 124 perangkat yang terdampak anomali dengan tingkat keparahan CRITICAL, HIGH, dan MEDIUM yang memerlukan investigasi prioritas untuk memastikan stabilitas jaringan. Meskipun tidak ada `subnet` yang melebihi batas kritis, penanganan anomali tersebut harus segera dilakukan untuk mencegah potensi gangguan layanan lebih lanjut.

---

## 1. Ringkasan Status

Kondisi saat ini masih dalam batas normal karena rasio `waiting` sebesar 9.2% berada di bawah ambang batas 10%. Mayoritas perangkat telah berhasil mendapatkan `lease` dengan status `bound`, menunjukkan operasional `DHCP server` yang stabil. Namun, angka `waiting` yang mendekati batas toleransi perlu dipantau agar tidak melampaui threshold yang ditetapkan.

| Status | Jumlah | Persentase |
|---|---|---|
| **Bound** | 1666 | 90.8% |
| **Waiting** | 168 | 9.2% |
| **Disabled (X)** | 0 | 0.0% |
| **Total** | **1834** | 100% |

## 3. 📊 Utilisasi IP Pool

Dengan total 24 `subnet` yang aktif dan tidak adanya `subnet` dalam kategori kritis atau waspada, utilisasi `IP pool` saat ini sangat sehat dan aman. Tidak ada risiko kekurangan `IP address` dalam waktu dekat, sehingga tidak diperlukan tindakan ekspansi `pool` atau konfigurasi ulang `DHCP server`. Tim dapat melanjutkan pemantauan rutin tanpa intervensi segera.

| Subnet | Used | Total (/24) | Usage % | Status |
|---|---|---|---|---|
| 10.39.1.0/24 | 174 | 254 | 68.5% | 🟢 Normal |
| 10.27.60.0/24 | 173 | 254 | 68.1% | 🟢 Normal |
| 10.27.57.0/24 | 142 | 254 | 55.9% | 🟢 Normal |
| 10.22.13.0/24 | 134 | 254 | 52.8% | 🟢 Normal |
| 10.27.59.0/24 | 129 | 254 | 50.8% | 🟢 Normal |
| 10.39.0.0/24 | 117 | 254 | 46.1% | 🟢 Normal |
| 10.34.13.0/24 | 104 | 254 | 40.9% | 🟢 Normal |
| 10.23.82.0/24 | 96 | 254 | 37.8% | 🟢 Normal |
| 10.27.58.0/24 | 84 | 254 | 33.1% | 🟢 Normal |
| 10.36.16.0/24 | 84 | 254 | 33.1% | 🟢 Normal |
| 10.24.8.0/24 | 82 | 254 | 32.3% | 🟢 Normal |
| 10.21.192.0/24 | 68 | 254 | 26.8% | 🟢 Normal |
| 10.30.90.0/24 | 59 | 254 | 23.2% | 🟢 Normal |
| 10.28.160.0/24 | 57 | 254 | 22.4% | 🟢 Normal |
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
| Bound + UTBK-OS | 1554 |
| Bound + Other (non-UTBK) | 112 |
| **Total UTBK-OS** | **1554** |

> **Rasio UTBK-OS terhadap Bound:** 93.3% (1554 dari 1666 perangkat bound adalah UTBK-OS)

## 5. Ringkasan per Server DHCP

Distribusi beban sangat tidak merata, dengan `dti-dhcp-lab-tik` dan `fk-1-LAB_Lt.1` masing-masing menangani hampir dua ratus perangkat `bound`, sementara sebagian besar server lain melayani di bawah seratus. Server `dti-dhcp-lab-tik` menjadi beban tertinggi dengan 92 perangkat dalam status `waiting`, jauh melampaui server lain yang hanya mencatat puluhan atau nol, menandakan potensi bottleneck atau masalah konfigurasi yang perlu segera diinvestigasi.

| Server | Bound | Waiting | Disabled | Total | UTBK-OS | Other |
|---|---|---|---|---|---|---|
| dti-dhcp-lab-tik | 199 | 92 | 0 | 291 | 196 | 3 |
| fapet-network-Lab | 21 | 2 | 0 | 23 | 21 | 0 |
| feb-CBT | 134 | 0 | 0 | 134 | 134 | 0 |
| fh-lab | 68 | 0 | 0 | 68 | 68 | 0 |
| fia-dhcp-2380-lab | 113 | 23 | 0 | 136 | 110 | 3 |
| fib-server-lab | 47 | 1 | 0 | 48 | 45 | 2 |
| filkom-G1.2-vlan3498 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.3-vlan3495 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.4-vlan3496 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.5-vlan3499 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.6-vlan3497 | 26 | 0 | 0 | 26 | 26 | 0 |
| fisip-serverpoollab | 46 | 7 | 0 | 53 | 46 | 0 |
| fk-1-LAB_Lt.1 | 172 | 1 | 0 | 173 | 94 | 78 |
| fk-8-dhcp_LabA | 115 | 14 | 0 | 129 | 114 | 1 |
| fk-8-dhcp_LabB | 139 | 3 | 0 | 142 | 136 | 3 |
| fk-8-dhcp_LabC | 84 | 0 | 0 | 84 | 68 | 16 |
| fkg-dhcp2 | 73 | 11 | 0 | 84 | 67 | 6 |
| fp-lab | 72 | 10 | 0 | 82 | 72 | 0 |
| fpik-serverlabutbk | 55 | 2 | 0 | 57 | 55 | 0 |
| ft-dekanat-Lab-66-pimp | 57 | 0 | 0 | 57 | 57 | 0 |
| ft-gbe-Lab-67-Admin | 29 | 0 | 0 | 29 | 29 | 0 |
| ftp-dhcp7 | 58 | 1 | 0 | 59 | 58 | 0 |
| vokasi-3508-serverpoollab | 54 | 1 | 0 | 55 | 54 | 0 |

## 6. Perangkat Bound Non-UTBK-OS

### Server: dti-dhcp-lab-tik

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.39.0.238 | 94:3F:C2:87:B2:E8 | sw-lab-4-barat-belakang | sw-grl-4-lab3-barat-belakang | - |
| 10.39.0.9 | E8:F7:24:17:EC:F0 | - | sw-grl-3-tik-lab1-atas | - |
| 10.39.0.82 | 28:C9:7A:FC:5C:63 | sw-lab4-selatan | H3C-fc5c63 | 1d39m1s |

### Server: fia-dhcp-2380-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.23.82.32 | 30:9C:23:C1:62:17 | - | DESKTOP-UTR5SS5 | - |
| 10.23.82.110 | 8C:85:C1:B5:A9:CE | - | - | - |
| 10.23.82.119 | 8C:32:23:32:30:31 | - | DESKTOP-HQ47QG3 | - |

### Server: fib-server-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.32.8.150 | EC:9B:8B:78:4B:8E | sw-lab-1 | HPE | - |
| 10.32.8.151 | EC:9B:8B:78:49:5E | sw-lab-2 | HPE | - |

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
| 10.27.60.74 | 10:FF:E0:66:70:82 | - | pxeutbk | 5d6h24m43s |
| 10.27.60.76 | 14:CB:19:0C:57:C3 | - | - | 3d23h50m35s |

### Server: fk-8-dhcp_LabA

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.59.50 | D4:61:37:0D:09:28 | - | - | - |

### Server: fk-8-dhcp_LabB

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.57.64 | EC:8E:B5:D7:B2:E1 | - | UB-B-WS246 | - |
| 10.27.57.42 | EC:8E:B5:D7:AA:C9 | - | UB-B-WS178 | - |
| 10.27.57.116 | EC:8E:B5:D7:AB:73 | - | UB-B-WS187 | - |

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

## 8. 📍 Anomali per Router

Distribusi anomali tersebar di enam `router` dengan total 124 perangkat terdampak, namun volume kejadian untuk setiap kategori (CRITICAL, HIGH, MEDIUM) sangat minim (hanya satu kasus per level). Karena tidak ada dominasi jumlah yang signifikan pada satu `router` tertentu, prioritas penanganan harus didasarkan pada dampak operasional, di mana `fia-dhcp-2380-lab` dan `fpik-serverlabutbk` perlu diinvestigasi lebih lanjut sebagai titik awal karena sering menjadi pusat layanan DHCP di lingkungan akademik.

### dti-dhcp-lab-tik (4 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w1d7h43m45s |
| 🔴 CRITICAL | 10.39.0.236 | - | dti-dhcp-lab-tik | Waiting: 1w6d5h58m6s |
| 🔴 CRITICAL | 10.39.0.7 | - | dti-dhcp-lab-tik | Waiting: 1w6d3h3m18s |
| 🔴 HIGH | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w1d7h43m45s |

### fia-dhcp-2380-lab (40 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.23.80.6 | DESKTOP-C75KJDC | fia-dhcp-2380-lab | Waiting: 20w5d3h3m44s |
| 🔴 CRITICAL | 10.23.80.43 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h30m19s |
| 🔴 CRITICAL | 10.23.80.44 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h29m59s |
| 🔴 CRITICAL | 10.23.80.36 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m36s |
| 🔴 CRITICAL | 10.23.80.38 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m30s |
| 🔴 CRITICAL | 10.23.80.40 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m20s |
| 🔴 CRITICAL | 10.23.80.42 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m13s |
| 🔴 CRITICAL | 10.23.80.39 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d6h51m10s |
| 🔴 CRITICAL | 10.23.80.34 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m17s |
| 🔴 CRITICAL | 10.23.80.31 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m10s |
| 🔴 CRITICAL | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m9s |
| 🔴 CRITICAL | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m6s |
| 🔴 CRITICAL | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h58m44s |
| 🔴 CRITICAL | 10.23.80.32 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h44m19s |
| 🔴 CRITICAL | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h12m22s |
| 🔴 CRITICAL | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h8m52s |
| 🔴 CRITICAL | 10.23.80.25 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w6d6h14m44s |
| 🔴 CRITICAL | 10.23.80.41 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w3d23h44m29s |
| 🔴 CRITICAL | 10.23.80.37 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 17w5d4h19m19s |
| 🔴 CRITICAL | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 17w5d4h15m59s |
| 🔴 HIGH | 10.23.80.6 | DESKTOP-C75KJDC | fia-dhcp-2380-lab | Waiting: 20w5d3h3m44s |
| 🔴 HIGH | 10.23.80.43 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h30m19s |
| 🔴 HIGH | 10.23.80.44 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h29m59s |
| 🔴 HIGH | 10.23.80.36 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m36s |
| 🔴 HIGH | 10.23.80.38 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m30s |
| 🔴 HIGH | 10.23.80.40 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m20s |
| 🔴 HIGH | 10.23.80.42 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d7h25m13s |
| 🔴 HIGH | 10.23.80.39 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d6h51m10s |
| 🔴 HIGH | 10.23.80.34 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m17s |
| 🔴 HIGH | 10.23.80.31 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m10s |
| 🔴 HIGH | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m9s |
| 🔴 HIGH | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h59m6s |
| 🔴 HIGH | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h58m44s |
| 🔴 HIGH | 10.23.80.32 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h44m19s |
| 🔴 HIGH | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h12m22s |
| 🔴 HIGH | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d2h8m52s |
| 🔴 HIGH | 10.23.80.25 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w6d6h14m44s |
| 🔴 HIGH | 10.23.80.41 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w3d23h44m29s |
| 🔴 HIGH | 10.23.80.37 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 17w5d4h19m19s |
| 🔴 HIGH | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 17w5d4h15m59s |

### fib-server-lab (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.32.8.100 | DESKTOP-14IMVL4 | fib-server-lab | Waiting: 12w2d22h59m28s |
| 🔴 HIGH | 10.32.8.100 | DESKTOP-14IMVL4 | fib-server-lab | Waiting: 12w2d22h59m28s |

### fisip-serverpoollab (52 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.31.16.54 | LAB-A24 | fisip-serverpoollab | Waiting: 22w4d6h47m34s |
| 🔴 CRITICAL | 10.31.16.55 | LAB-A25 | fisip-serverpoollab | Waiting: 22w4d6h47m34s |
| 🔴 CRITICAL | 10.31.16.73 | LAB-B18 | fisip-serverpoollab | Waiting: 22w4d6h41m57s |
| 🔴 CRITICAL | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 22w4d6h29m54s |
| 🔴 CRITICAL | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 22w4d6h29m46s |
| 🔴 CRITICAL | 10.31.16.53 | LAB-A23 | fisip-serverpoollab | Waiting: 22w4d6h20m54s |
| 🔴 HIGH | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 9w5d4h45m15s |
| 🔴 HIGH | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 9w5d4h44m58s |
| 🔴 HIGH | 10.31.16.55 | LAB-A25 | fisip-serverpoollab | Waiting: 9w5d3h26m40s |
| 🟡 MEDIUM | 10.31.16.47 | utbk-os | fisip-serverpoollab | Age: 22w4d6h54m53s |
| 🟡 MEDIUM | 10.31.16.48 | utbk-os | fisip-serverpoollab | Age: 22w4d6h52m59s |
| 🟡 MEDIUM | 10.31.16.50 | utbk-os | fisip-serverpoollab | Age: 22w4d6h52m11s |
| 🟡 MEDIUM | 10.31.16.49 | utbk-os | fisip-serverpoollab | Age: 22w4d6h51m15s |
| 🟡 MEDIUM | 10.31.16.52 | utbk-os | fisip-serverpoollab | Age: 22w4d6h51m10s |
| 🟡 MEDIUM | 10.31.16.43 | utbk-os | fisip-serverpoollab | Age: 22w4d6h44m7s |
| 🟡 MEDIUM | 10.31.16.31 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m42s |
| 🟡 MEDIUM | 10.31.16.32 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m40s |
| 🟡 MEDIUM | 10.31.16.33 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m39s |
| 🟡 MEDIUM | 10.31.16.34 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m37s |
| 🟡 MEDIUM | 10.31.16.35 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m35s |
| 🟡 MEDIUM | 10.31.16.36 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m33s |
| 🟡 MEDIUM | 10.31.16.37 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m31s |
| 🟡 MEDIUM | 10.31.16.38 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m28s |
| 🟡 MEDIUM | 10.31.16.39 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m27s |
| 🟡 MEDIUM | 10.31.16.40 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m27s |
| 🟡 MEDIUM | 10.31.16.41 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m25s |
| 🟡 MEDIUM | 10.31.16.42 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m24s |
| 🟡 MEDIUM | 10.31.16.51 | utbk-os | fisip-serverpoollab | Age: 22w4d6h43m22s |
| 🟡 MEDIUM | 10.31.16.56 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m24s |
| 🟡 MEDIUM | 10.31.16.57 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m21s |
| 🟡 MEDIUM | 10.31.16.58 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m16s |
| 🟡 MEDIUM | 10.31.16.60 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m14s |
| 🟡 MEDIUM | 10.31.16.61 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m12s |
| 🟡 MEDIUM | 10.31.16.59 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m12s |
| 🟡 MEDIUM | 10.31.16.67 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m9s |
| 🟡 MEDIUM | 10.31.16.62 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m8s |
| 🟡 MEDIUM | 10.31.16.63 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m6s |
| 🟡 MEDIUM | 10.31.16.66 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m5s |
| 🟡 MEDIUM | 10.31.16.65 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m4s |
| 🟡 MEDIUM | 10.31.16.64 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m2s |
| 🟡 MEDIUM | 10.31.16.69 | utbk-os | fisip-serverpoollab | Age: 22w4d6h42m1s |
| 🟡 MEDIUM | 10.31.16.70 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m59s |
| 🟡 MEDIUM | 10.31.16.71 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m56s |
| 🟡 MEDIUM | 10.31.16.77 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m54s |
| 🟡 MEDIUM | 10.31.16.76 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m52s |
| 🟡 MEDIUM | 10.31.16.78 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m51s |
| 🟡 MEDIUM | 10.31.16.75 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m50s |
| 🟡 MEDIUM | 10.31.16.74 | utbk-os | fisip-serverpoollab | Age: 22w4d6h41m45s |
| 🟡 MEDIUM | 10.31.16.46 | utbk-os | fisip-serverpoollab | Age: 22w4d6h36m57s |
| 🟡 MEDIUM | 10.31.16.45 | utbk-os | fisip-serverpoollab | Age: 22w4d6h36m56s |
| 🟡 MEDIUM | 10.31.16.44 | utbk-os | fisip-serverpoollab | Age: 22w4d6h31m16s |
| 🟡 MEDIUM | 10.31.16.68 | utbk-os | fisip-serverpoollab | Age: 22w4d6h26m33s |

### fpik-serverlabutbk (24 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🟡 MEDIUM | 10.28.160.121 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h45m5s |
| 🟡 MEDIUM | 10.28.160.187 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h45m1s |
| 🟡 MEDIUM | 10.28.160.145 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m49s |
| 🟡 MEDIUM | 10.28.160.122 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m31s |
| 🟡 MEDIUM | 10.28.160.97 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m26s |
| 🟡 MEDIUM | 10.28.160.125 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m20s |
| 🟡 MEDIUM | 10.28.160.82 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m19s |
| 🟡 MEDIUM | 10.28.160.115 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m16s |
| 🟡 MEDIUM | 10.28.160.92 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m15s |
| 🟡 MEDIUM | 10.28.160.123 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m1s |
| 🟡 MEDIUM | 10.28.160.94 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h44m1s |
| 🟡 MEDIUM | 10.28.160.116 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m57s |
| 🟡 MEDIUM | 10.28.160.127 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m42s |
| 🟡 MEDIUM | 10.28.160.102 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m41s |
| 🟡 MEDIUM | 10.28.160.109 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m33s |
| 🟡 MEDIUM | 10.28.160.107 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m25s |
| 🟡 MEDIUM | 10.28.160.55 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m14s |
| 🟡 MEDIUM | 10.28.160.108 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m14s |
| 🟡 MEDIUM | 10.28.160.93 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h43m11s |
| 🟡 MEDIUM | 10.28.160.96 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h42m54s |
| 🟡 MEDIUM | 10.28.160.129 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h42m42s |
| 🟡 MEDIUM | 10.28.160.128 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h40m4s |
| 🟡 MEDIUM | 10.28.160.98 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h40m2s |
| 🟡 MEDIUM | 10.28.160.99 | utbk-os | fpik-serverlabutbk | Age: 2w6d6h39m23s |

### vokasi-3508-serverpoollab (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.35.80.83 | 555606b | vokasi-3508-serverpoollab | Waiting: 448w4d12h47m7s |
| 🔴 HIGH | 10.35.80.83 | 555606b | vokasi-3508-serverpoollab | Waiting: 448w4d12h47m7s |

## 9. ⚠️ ANOMALI TERDETEKSI

Tiga puluh satu perangkat dalam status `waiting` selama lebih dari 31 hari, dengan durasi ekstrem mencapai hampir 10 minggu, mengindikasikan kegagalan `lease` yang kronis dan perangkat yang kemungkinan besar tidak aktif atau rusak. Urgensi tinggi pada 26 entri yang tidak pernah terlihat lebih dari dua minggu serta 67 kasus `bound` melebihi batas wajar menuntut tindakan segera untuk `disabled` atau menghapus entri tersebut guna membebaskan slot di `IP pool` dan menjaga integritas `DHCP server`.

### 🔴 ANOMALI 1: Perangkat Waiting Sudah Berhari-hari (CRITICAL)

Terdapat **31 perangkat waiting** yang sudah mencoba mendapatkan IP selama lebih dari 1 hari.

| IP | Comment | Hostname | MAC | Durasi |
|---|---|---|---|---|
| 10.35.80.83 | BACKUP | 555606b | 78:45:C4:07:9E:E9 | 448w4d12h47m7s |
| 10.31.16.54 | - | LAB-A24 | 08:8F:C3:BE:4F:D9 | 22w4d6h47m34s |
| 10.31.16.55 | - | LAB-A25 | 08:8F:C3:BE:4E:4D | 22w4d6h47m34s |
| 10.31.16.73 | - | LAB-B18 | 08:8F:C3:BC:10:C8 | 22w4d6h41m57s |
| 10.31.16.79 | - | LAB-B24 | 08:8F:C3:BE:4F:CD | 22w4d6h29m54s |
| 10.31.16.80 | - | LAB-B25 | 08:8F:C3:BE:4F:98 | 22w4d6h29m46s |
| 10.31.16.53 | - | LAB-A23 | 08:8F:C3:BE:4C:D4 | 22w4d6h20m54s |
| 10.23.80.6 | LAB-UTBK-2 | DESKTOP-C75KJDC | E4:E7:49:51:FA:F8 | 20w5d3h3m44s |
| 10.23.80.43 | LAB-UTBK-39 | LAB-SIM-01 | 70:F3:95:01:2D:78 | 19w4d7h30m19s |
| 10.23.80.44 | LAB-UTBK-40 | LAB-SIM-01 | 00:24:7E:0A:85:C1 | 19w4d7h29m59s |
| 10.23.80.36 | LAB-UTBK-32 | LAB-SIM-01 | 00:24:7E:0A:85:42 | 19w4d7h25m36s |
| 10.23.80.38 | LAB-UTBK-34 | LAB-SIM-01 | 00:24:7E:0A:84:33 | 19w4d7h25m30s |
| 10.23.80.40 | LAB-UTBK-36 | LAB-SIM-01 | 00:24:7E:0A:84:7A | 19w4d7h25m20s |
| 10.23.80.42 | LAB-UTBK-38 | LAB-SIM-01 | 00:24:7E:0A:83:EC | 19w4d7h25m13s |
| 10.23.80.39 | LAB-UTBK-35 | LAB-SIM-01 | 00:24:7E:0A:4C:42 | 19w4d6h51m10s |
| 10.23.80.34 | LAB-UTBK-30 | LAB-SIM-01 | 00:10:C6:B0:E1:26 | 19w4d2h59m17s |
| 10.23.80.31 | LAB-UTBK-27 | LAB-SIM-01 | 00:10:C6:B0:E0:92 | 19w4d2h59m10s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 70:F3:95:01:2E:40 | 19w4d2h59m9s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 00:24:7E:0A:83:CE | 19w4d2h59m6s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 00:24:7E:0A:84:0E | 19w4d2h58m44s |
| 10.23.80.32 | LAB-UTBK-28 | LAB-SIM-01 | 00:24:7E:0A:83:C9 | 19w4d2h44m19s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 00:24:7E:0A:84:04 | 19w4d2h12m22s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 00:24:7E:0A:83:E5 | 19w4d2h8m52s |
| 10.23.80.25 | LAB-UTBK-21 | LAB-SIM-01 | 00:24:7E:0A:85:C0 | 18w6d6h14m44s |
| 10.23.80.41 | LAB-UTBK-37 | LAB-SIM-01 | 00:24:7E:0A:4C:1D | 18w3d23h44m29s |
| 10.23.80.37 | LAB-UTBK-33 | LAB-SIM-01 | 70:F3:95:01:2E:0D | 17w5d4h19m19s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 00:24:7E:0A:84:21 | 17w5d4h15m59s |
| 10.32.8.100 | - | DESKTOP-14IMVL4 | 8C:EC:4B:B8:5E:65 | 12w2d22h59m28s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 28:C9:7A:FC:58:2B | 2w1d7h43m45s |
| 10.39.0.236 | - | - | 80:BC:37:2C:C7:E0 | 1w6d5h58m6s |
| 10.39.0.7 | - | - | C8:A6:08:04:C5:50 | 1w6d3h3m18s |

**Rekomendasi:** Cek koneksi fisik dan konfigurasi DHCP client. Jika tidak digunakan, disable entri.

---

### 🔴 ANOMALI 2: Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu (HIGH)

Terdapat **26 perangkat waiting** yang `last-seen` sudah lebih dari 2 minggu.

| IP | Comment | Hostname | Last Seen |
|---|---|---|---|
| 10.35.80.83 | BACKUP | 555606b | 448w4d12h47m7s |
| 10.23.80.6 | LAB-UTBK-2 | DESKTOP-C75KJDC | 20w5d3h3m44s |
| 10.23.80.43 | LAB-UTBK-39 | LAB-SIM-01 | 19w4d7h30m19s |
| 10.23.80.44 | LAB-UTBK-40 | LAB-SIM-01 | 19w4d7h29m59s |
| 10.23.80.36 | LAB-UTBK-32 | LAB-SIM-01 | 19w4d7h25m36s |
| 10.23.80.38 | LAB-UTBK-34 | LAB-SIM-01 | 19w4d7h25m30s |
| 10.23.80.40 | LAB-UTBK-36 | LAB-SIM-01 | 19w4d7h25m20s |
| 10.23.80.42 | LAB-UTBK-38 | LAB-SIM-01 | 19w4d7h25m13s |
| 10.23.80.39 | LAB-UTBK-35 | LAB-SIM-01 | 19w4d6h51m10s |
| 10.23.80.34 | LAB-UTBK-30 | LAB-SIM-01 | 19w4d2h59m17s |
| 10.23.80.31 | LAB-UTBK-27 | LAB-SIM-01 | 19w4d2h59m10s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 19w4d2h59m9s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 19w4d2h59m6s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 19w4d2h58m44s |
| 10.23.80.32 | LAB-UTBK-28 | LAB-SIM-01 | 19w4d2h44m19s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 19w4d2h12m22s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 19w4d2h8m52s |
| 10.23.80.25 | LAB-UTBK-21 | LAB-SIM-01 | 18w6d6h14m44s |
| 10.23.80.41 | LAB-UTBK-37 | LAB-SIM-01 | 18w3d23h44m29s |
| 10.23.80.37 | LAB-UTBK-33 | LAB-SIM-01 | 17w5d4h19m19s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 17w5d4h15m59s |
| 10.32.8.100 | - | DESKTOP-14IMVL4 | 12w2d22h59m28s |
| 10.31.16.79 | - | LAB-B24 | 9w5d4h45m15s |
| 10.31.16.80 | - | LAB-B25 | 9w5d4h44m58s |
| 10.31.16.55 | - | LAB-A25 | 9w5d3h26m40s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 2w1d7h43m45s |

**Rekomendasi:** Disable/hapus entri ini untuk bebaskan IP pool.

---

### 🟡 ANOMALI 3: Perangkat Bound Terlalu Lama (> 3 Hari) (MEDIUM)

Terdapat **67 perangkat bound** yang sudah lebih dari 3 hari.

| IP | Comment | Hostname | Age | Expires After |
|---|---|---|---|---|
| 10.31.16.47 | - | utbk-os | 22w4d6h54m53s | 37m8s |
| 10.31.16.48 | - | utbk-os | 22w4d6h52m59s | 37m9s |
| 10.31.16.50 | - | utbk-os | 22w4d6h52m11s | 43m47s |
| 10.31.16.49 | - | utbk-os | 22w4d6h51m15s | 40m47s |
| 10.31.16.52 | - | utbk-os | 22w4d6h51m10s | 37m25s |
| 10.31.16.43 | - | utbk-os | 22w4d6h44m7s | 37m23s |
| 10.31.16.31 | - | utbk-os | 22w4d6h43m42s | 36m20s |
| 10.31.16.32 | - | utbk-os | 22w4d6h43m40s | 36m22s |
| 10.31.16.33 | - | utbk-os | 22w4d6h43m39s | 36m23s |
| 10.31.16.34 | - | utbk-os | 22w4d6h43m37s | 36m44s |
| 10.31.16.35 | - | utbk-os | 22w4d6h43m35s | 55m28s |
| 10.31.16.36 | - | utbk-os | 22w4d6h43m33s | 36m45s |
| 10.31.16.37 | - | utbk-os | 22w4d6h43m31s | 37m8s |
| 10.31.16.38 | - | utbk-os | 22w4d6h43m28s | 37m4s |
| 10.31.16.39 | - | utbk-os | 22w4d6h43m27s | 37m2s |
| 10.31.16.40 | - | utbk-os | 22w4d6h43m27s | 37m19s |
| 10.31.16.41 | - | utbk-os | 22w4d6h43m25s | 37m20s |
| 10.31.16.42 | - | utbk-os | 22w4d6h43m24s | 37m26s |
| 10.31.16.51 | - | utbk-os | 22w4d6h43m22s | 37m37s |
| 10.31.16.56 | - | utbk-os | 22w4d6h42m24s | 32m24s |
| 10.31.16.57 | - | utbk-os | 22w4d6h42m21s | 32m36s |
| 10.31.16.58 | - | utbk-os | 22w4d6h42m16s | 32m47s |
| 10.31.16.60 | - | utbk-os | 22w4d6h42m14s | 33m3s |
| 10.31.16.61 | - | utbk-os | 22w4d6h42m12s | 32m55s |
| 10.31.16.59 | - | utbk-os | 22w4d6h42m12s | 32m50s |
| 10.31.16.67 | - | utbk-os | 22w4d6h42m9s | 33m49s |
| 10.31.16.62 | - | utbk-os | 22w4d6h42m8s | 33m12s |
| 10.31.16.63 | - | utbk-os | 22w4d6h42m6s | 33m5s |
| 10.31.16.66 | - | utbk-os | 22w4d6h42m5s | 34m39s |
| 10.31.16.65 | - | utbk-os | 22w4d6h42m4s | 33m36s |
| 10.31.16.64 | - | utbk-os | 22w4d6h42m2s | 33m6s |
| 10.31.16.69 | - | utbk-os | 22w4d6h42m1s | 33m42s |
| 10.31.16.70 | - | utbk-os | 22w4d6h41m59s | 33m37s |
| 10.31.16.71 | - | utbk-os | 22w4d6h41m56s | 33m6s |
| 10.31.16.77 | - | utbk-os | 22w4d6h41m54s | 33m41s |
| 10.31.16.76 | - | utbk-os | 22w4d6h41m52s | 33m21s |
| 10.31.16.78 | - | utbk-os | 22w4d6h41m51s | 33m22s |
| 10.31.16.75 | - | utbk-os | 22w4d6h41m50s | 57m55s |
| 10.31.16.74 | - | utbk-os | 22w4d6h41m45s | 33m29s |
| 10.31.16.46 | - | utbk-os | 22w4d6h36m57s | 37m18s |
| 10.31.16.45 | - | utbk-os | 22w4d6h36m56s | 37m17s |
| 10.31.16.44 | - | utbk-os | 22w4d6h31m16s | 37m17s |
| 10.31.16.68 | - | utbk-os | 22w4d6h26m33s | 33m44s |
| 10.28.160.121 | - | utbk-os | 2w6d6h45m5s | 26m15s |
| 10.28.160.187 | - | utbk-os | 2w6d6h45m1s | 26m16s |
| 10.28.160.145 | - | utbk-os | 2w6d6h44m49s | 25m56s |
| 10.28.160.122 | - | utbk-os | 2w6d6h44m31s | 25m54s |
| 10.28.160.97 | - | utbk-os | 2w6d6h44m26s | 25m54s |
| 10.28.160.125 | - | utbk-os | 2w6d6h44m20s | 26m33s |
| 10.28.160.82 | - | utbk-os | 2w6d6h44m19s | 26m29s |
| 10.28.160.115 | - | utbk-os | 2w6d6h44m16s | 26m36s |
| 10.28.160.92 | - | utbk-os | 2w6d6h44m15s | 15m42s |
| 10.28.160.123 | - | utbk-os | 2w6d6h44m1s | 27m27s |
| 10.28.160.94 | - | utbk-os | 2w6d6h44m1s | 27m19s |
| 10.28.160.116 | - | utbk-os | 2w6d6h43m57s | 27m22s |
| 10.28.160.127 | - | utbk-os | 2w6d6h43m42s | 27m40s |
| 10.28.160.102 | - | utbk-os | 2w6d6h43m41s | 27m40s |
| 10.28.160.109 | - | utbk-os | 2w6d6h43m33s | 27m48s |
| 10.28.160.107 | - | utbk-os | 2w6d6h43m25s | 27m50s |
| 10.28.160.55 | - | utbk-os | 2w6d6h43m14s | 28m12s |
| 10.28.160.108 | - | utbk-os | 2w6d6h43m14s | 28m21s |
| 10.28.160.93 | - | utbk-os | 2w6d6h43m11s | 28m11s |
| 10.28.160.96 | - | utbk-os | 2w6d6h42m54s | 24m41s |
| 10.28.160.129 | - | utbk-os | 2w6d6h42m42s | 28m14s |
| 10.28.160.128 | - | utbk-os | 2w6d6h40m4s | 17m |
| 10.28.160.98 | - | utbk-os | 2w6d6h40m2s | 28m23s |
| 10.28.160.99 | - | utbk-os | 2w6d6h39m23s | 29m24s |

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

*Report generated: 21 April 2026*
