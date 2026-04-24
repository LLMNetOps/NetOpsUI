# 📊 Laporan DHCP Lease — 24 April 2026

**Tanggal:** 24 April 2026
**Total Server:** 23
**File Sumber:** 23 file di direktori `output/`
**Perbandingan:** 1821 perangkat hari ini vs 3653 perangkat hari sebelumnya

---

## 🗒️ Ringkasan Eksekutif

Status `lease` menunjukkan tren positif signifikan dengan lonjakan `bound` sebesar 809 perangkat dan penurunan `waiting` sebesar 807 perangkat dibandingkan hari sebelumnya, mengindikasikan stabilitas jaringan yang membaik. Meskipun tidak ada `subnet` yang mencapai ambang batas kritis di atas 90%, terdapat 58 perangkat yang terdampak oleh tiga jenis anomali dengan tingkat keparahan CRITICAL, HIGH, dan MEDIUM yang memerlukan investigasi segera. Dominasi perangkat `bound` pada kategori UTBK-OS sebesar 87.9% dari total 1667 perangkat aktif mengonfirmasi utilisasi `pool` yang sehat namun perlu dipantau agar tidak terjadi kelangkaan `IP address` di masa depan. Disarankan untuk segera melakukan troubleshooting pada 58 perangkat anomali tersebut guna mencegah potensi gangguan layanan, sambil terus memantau tren pertumbuhan `bound` untuk penyesuaian `DHCP server` configuration jika diperlukan.

---

## 1. Ringkasan Status

Kondisi `lease` DHCP saat ini normal karena rasio `waiting` sebesar 8.5% masih berada di bawah ambang batas 10%. Mayoritas perangkat berhasil mendapatkan `IP address` dengan status `bound`, dan tidak ada entri `disabled`. Tidak diperlukan tindakan korektif segera.

| Status | Jumlah | Persentase |
|---|---|---|
| **Bound** | 1667 | 91.5% |
| **Waiting** | 154 | 8.5% |
| **Disabled (X)** | 0 | 0.0% |
| **Total** | **1821** | 100% |

## 2. 📈 Tren Historis (7 Hari Terakhir)

Lonjakan signifikan pada `bound` sebesar 809 entri disertai penurunan drastis `waiting` sebanyak 807 entri mengindikasikan proses distribusi `IP address` yang sedang berlangsung secara masif. Tren ini menunjukkan pemulihan kapasitas `pool` setelah kondisi `waiting` yang tinggi pada 22 April, yang sebelumnya mengisyaratkan potensi bottleneck pada `DHCP server`.

| Tanggal | Bound | Waiting | Total |
|---|---|---|---|
| 21 April 2026 | 1666 | 168 | 1834 |
| 22 April 2026 | 858 | 961 | 1819 |
| 24 April 2026 | 1667 | 154 | 1821 |

## 3. 📊 Utilisasi IP Pool

Secara keseluruhan `IP pool` masih aman, namun `subnet` `10.39.0.0/24` sudah masuk kategori waspada dengan utilisasi mendekati 80%. Jika pertumbuhan perangkat berlanjut, ekspansi `pool` perlu dipertimbangkan dalam waktu dekat.

| Subnet | Used | Total (/24) | Usage % | Status |
|---|---|---|---|---|
| 10.39.0.0/24 | 197 | 254 | 77.6% | 🟡 Waspada |
| 10.27.60.0/24 | 173 | 254 | 68.1% | 🟢 Normal |
| 10.27.57.0/24 | 143 | 254 | 56.3% | 🟢 Normal |
| 10.22.13.0/24 | 134 | 254 | 52.8% | 🟢 Normal |
| 10.27.59.0/24 | 130 | 254 | 51.2% | 🟢 Normal |
| 10.34.13.0/24 | 104 | 254 | 40.9% | 🟢 Normal |
| 10.23.82.0/24 | 96 | 254 | 37.8% | 🟢 Normal |
| 10.27.58.0/24 | 84 | 254 | 33.1% | 🟢 Normal |
| 10.36.16.0/24 | 84 | 254 | 33.1% | 🟢 Normal |
| 10.24.8.0/24 | 82 | 254 | 32.3% | 🟢 Normal |
| 10.39.1.0/24 | 76 | 254 | 29.9% | 🟢 Normal |
| 10.21.192.0/24 | 68 | 254 | 26.8% | 🟢 Normal |
| 10.28.160.0/24 | 60 | 254 | 23.6% | 🟢 Normal |
| 10.30.90.0/24 | 59 | 254 | 23.2% | 🟢 Normal |
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
| Bound + UTBK-OS | 1466 |
| Bound + Other (non-UTBK) | 201 |
| **Total UTBK-OS** | **1466** |

> **Rasio UTBK-OS terhadap Bound:** 87.9% (1466 dari 1667 perangkat bound adalah UTBK-OS)

## 5. Ringkasan per Server DHCP

Distribusi beban antar `DHCP server` sangat tidak merata, dengan `dti-dhcp-lab-tik` dan `fk-1-LAB_Lt.1` masing-masing menangani hampir dua ratus perangkat `bound`, sementara sebagian besar server lain hanya melayani puluhan. Server `dti-dhcp-lab-tik` mencatat konsentrasi `waiting` tertinggi dengan tujuh puluh empat antrian, yang jauh melampaui beban antrian di server lain dan mengindikasikan potensi bottleneck atau masalah konfigurasi yang perlu segera ditindaklanjuti.

| Server | Bound | Waiting | Disabled | Total | UTBK-OS | Other |
|---|---|---|---|---|---|---|
| dti-dhcp-lab-tik | 199 | 74 | 0 | 273 | 196 | 3 |
| fapet-network-Lab | 22 | 1 | 0 | 23 | 22 | 0 |
| feb-CBT | 133 | 1 | 0 | 134 | 133 | 0 |
| fh-lab | 68 | 0 | 0 | 68 | 68 | 0 |
| fia-dhcp-2380-lab | 111 | 25 | 0 | 136 | 107 | 4 |
| fib-server-lab | 47 | 1 | 0 | 48 | 45 | 2 |
| filkom-G1.2-vlan3498 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.3-vlan3495 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.4-vlan3496 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.5-vlan3499 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.6-vlan3497 | 26 | 0 | 0 | 26 | 26 | 0 |
| fisip-serverpoollab | 46 | 7 | 0 | 53 | 46 | 0 |
| fk-1-LAB_Lt.1 | 168 | 5 | 0 | 173 | 0 | 168 |
| fk-8-dhcp_LabA | 116 | 14 | 0 | 130 | 114 | 2 |
| fk-8-dhcp_LabB | 138 | 5 | 0 | 143 | 137 | 1 |
| fk-8-dhcp_LabC | 83 | 1 | 0 | 84 | 68 | 15 |
| fkg-dhcp2 | 73 | 11 | 0 | 84 | 67 | 6 |
| fp-lab | 77 | 5 | 0 | 82 | 77 | 0 |
| fpik-serverlabutbk | 58 | 2 | 0 | 60 | 58 | 0 |
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
| 10.39.0.82 | 28:C9:7A:FC:5C:63 | sw-Lab4-selatan | H3C-fc5c63 | 3d21h39m49s |

### Server: fia-dhcp-2380-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.23.82.32 | 30:9C:23:C1:62:17 | - | DESKTOP-UTR5SS5 | - |
| 10.23.82.110 | 8C:85:C1:B5:A9:CE | - | - | - |
| 10.23.80.20 | E4:E7:49:51:FB:C7 | LAB-UTBK-16 | DESKTOP-08EDGV3 | - |
| 10.23.80.15 | E4:E7:49:51:F7:D5 | LAB-UTBK-11 | DESKTOP-T0UQFR8 | - |

### Server: fib-server-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.32.8.150 | EC:9B:8B:78:4B:8E | sw-lab-1 | HPE | - |
| 10.32.8.151 | EC:9B:8B:78:49:5E | sw-lab-2 | HPE | - |

### Server: fk-1-LAB_Lt.1

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.60.91 | 14:CB:19:0B:EA:1F | - | debian | - |
| 10.27.60.120 | 14:CB:19:0B:EB:0E | - | - | - |
| 10.27.60.140 | 14:CB:19:0C:B8:1F | - | debian | - |
| 10.27.60.93 | 14:CB:19:0B:CA:BC | - | debian | - |
| 10.27.60.116 | 14:CB:19:0C:48:54 | - | - | - |
| 10.27.60.144 | E4:E7:49:51:FB:36 | - | UB-C-WS281 | - |
| 10.27.60.121 | 14:CB:19:0C:47:1C | - | - | - |
| 10.27.60.94 | 14:CB:19:0C:92:DB | - | debian | - |
| 10.27.60.183 | 14:CB:19:0C:48:FC | - | - | - |
| 10.27.60.128 | 14:CB:19:0C:48:E5 | - | debian | - |
| 10.27.60.181 | 14:CB:19:0C:68:55 | - | - | - |
| 10.27.60.192 | 14:CB:19:0C:18:34 | - | UB-A-WS065 | - |
| 10.27.60.180 | 14:CB:19:0C:08:98 | - | debian | - |
| 10.27.60.119 | 14:CB:19:0C:70:CD | - | - | - |
| 10.27.60.141 | 14:CB:19:0C:68:D6 | - | - | - |
| 10.27.60.186 | 14:CB:19:0C:37:3D | - | - | - |
| 10.27.60.143 | 14:CB:19:0C:D6:5B | - | - | - |
| 10.27.60.193 | 14:CB:19:0C:37:43 | - | - | - |
| 10.27.60.195 | 14:CB:19:0B:DB:0D | - | debian | - |
| 10.27.60.171 | E4:E7:49:51:FC:07 | - | debian | - |
| 10.27.60.179 | 14:CB:19:0C:D7:E7 | - | - | - |
| 10.27.60.114 | 14:CB:19:0C:52:B0 | - | - | - |
| 10.27.60.111 | 14:CB:19:0C:D3:81 | - | - | - |
| 10.27.60.127 | 14:CB:19:0C:67:0C | - | - | - |
| 10.27.60.188 | 14:CB:19:0C:A8:CE | - | - | - |
| 10.27.60.129 | 14:CB:19:0C:A2:00 | - | debian | - |
| 10.27.60.117 | 14:CB:19:0C:D3:11 | - | debian | - |
| 10.27.60.191 | 14:CB:19:0C:77:8F | - | debian | - |
| 10.27.60.115 | 14:CB:19:0C:37:2A | - | debian | - |
| 10.27.60.126 | 14:CB:19:0C:C7:12 | - | debian | - |
| 10.27.60.182 | 14:CB:19:0C:68:0B | - | - | - |
| 10.27.60.142 | 14:CB:19:0C:D3:48 | - | debian | - |
| 10.27.60.185 | 14:CB:19:0C:28:C6 | - | - | - |
| 10.27.60.189 | 14:CB:19:0C:17:69 | - | debian | - |
| 10.27.60.132 | E4:E7:49:51:F7:3E | - | - | - |
| 10.27.60.123 | 14:CB:19:0C:47:A6 | - | - | - |
| 10.27.60.145 | E4:E7:49:51:FB:FE | - | debian | - |
| 10.27.60.190 | 14:CB:19:0C:B6:9A | - | debian | - |
| 10.27.60.112 | 14:CB:19:0C:27:13 | - | - | - |
| 10.27.60.109 | E4:E7:49:51:F7:0D | - | UB-C-WS281 | - |
| 10.27.60.146 | E4:E7:49:51:F1:48 | - | - | - |
| 10.27.60.163 | E4:E7:49:51:F9:17 | - | - | - |
| 10.27.60.167 | E4:E7:49:51:F9:8E | - | - | - |
| 10.27.60.184 | 14:CB:19:0C:08:2A | - | - | - |
| 10.27.60.187 | 14:CB:19:0C:A8:B2 | - | debian | - |
| 10.27.60.178 | 14:CB:19:0C:A8:5B | - | - | - |
| 10.27.60.194 | 14:CB:19:0B:CB:7A | - | - | - |
| 10.27.60.177 | 14:CB:19:0B:CB:8E | - | debian | - |
| 10.27.60.122 | 14:CB:19:0C:58:1E | - | - | - |
| 10.27.60.166 | E4:E7:49:51:FA:54 | - | - | - |
| 10.27.60.105 | E4:E7:49:51:F6:04 | - | - | - |
| 10.27.60.118 | 14:CB:19:0C:38:5B | - | - | - |
| 10.27.60.113 | 14:CB:19:0C:47:57 | - | UB-A-WS065 | - |
| 10.27.60.131 | E4:E7:49:51:F9:0C | - | debian | - |
| 10.27.60.98 | E4:E7:49:51:F7:63 | - | - | - |
| 10.27.60.153 | E4:E7:49:51:F7:C9 | - | - | - |
| 10.27.60.99 | E4:E7:49:51:FB:3F | - | - | - |
| 10.27.60.225 | E4:E7:49:51:FB:3B | - | debian | - |
| 10.27.60.151 | E4:E7:49:51:F9:F8 | - | debian | - |
| 10.27.60.103 | E4:E7:49:51:FA:16 | - | debian | - |
| 10.27.60.168 | E4:E7:49:51:FA:0C | - | - | - |
| 10.27.60.149 | E4:E7:49:51:F6:34 | - | UB-C-WS281 | - |
| 10.27.60.104 | E4:E7:49:51:F8:5C | - | debian | - |
| 10.27.60.101 | E4:E7:49:51:F5:F7 | - | debian | - |
| 10.27.60.150 | E4:E7:49:51:FB:F6 | - | - | - |
| 10.27.60.237 | 14:CB:19:0C:38:AC | - | debian | - |
| 10.27.60.232 | 14:CB:19:0C:08:F2 | - | debian | - |
| 10.27.60.239 | 14:CB:19:0C:38:48 | - | debian | - |
| 10.27.60.209 | 14:CB:19:0C:68:7D | - | - | - |
| 10.27.60.228 | 14:CB:19:0C:08:08 | - | - | - |
| 10.27.60.227 | 14:CB:19:0C:24:4B | - | - | - |
| 10.27.60.244 | 14:CB:19:0C:68:3A | - | - | - |
| 10.27.60.206 | 14:CB:19:0C:18:77 | - | UB-A-WS065 | - |
| 10.27.60.233 | 14:CB:19:0C:37:56 | - | - | - |
| 10.27.60.214 | 14:CB:19:0C:C6:E9 | - | - | - |
| 10.27.60.240 | 14:CB:19:0C:82:B7 | - | - | - |
| 10.27.60.247 | 14:CB:19:0B:EB:20 | - | - | - |
| 10.27.60.230 | 14:CB:19:0C:24:28 | - | debian | - |
| 10.27.60.249 | 14:CB:19:0B:DB:70 | - | - | - |
| 10.27.60.248 | 14:CB:19:0B:CB:D4 | - | - | - |
| 10.27.60.238 | 14:CB:19:0C:D7:A2 | - | debian | - |
| 10.27.60.229 | 14:CB:19:0B:FA:E8 | - | debian | - |
| 10.27.60.196 | 14:CB:19:0C:68:0A | - | - | - |
| 10.27.60.136 | 14:CB:19:0C:57:3E | - | - | - |
| 10.27.60.130 | 14:CB:19:0C:F5:05 | - | debian | - |
| 10.27.60.212 | 14:CB:19:0C:A7:00 | - | - | - |
| 10.27.60.235 | 14:CB:19:0C:E7:12 | - | - | - |
| 10.27.60.95 | 14:CB:19:0C:18:58 | - | debian | - |
| 10.27.60.234 | 14:CB:19:0C:E3:5E | - | debian | - |
| 10.27.60.243 | 14:CB:19:0B:DB:8E | - | - | - |
| 10.27.60.241 | 14:CB:19:0C:92:2B | - | - | - |
| 10.27.60.242 | 14:CB:19:0C:B7:A4 | - | - | - |
| 10.27.60.231 | 14:CB:19:0C:18:C1 | - | - | - |
| 10.27.60.133 | 14:CB:19:0C:38:B9 | - | - | - |
| 10.27.60.92 | 14:CB:19:0C:52:FF | - | - | - |
| 10.27.60.236 | 14:CB:19:0C:08:E5 | - | - | - |
| 10.27.60.246 | 14:CB:19:0C:D6:AB | - | - | - |
| 10.27.60.245 | 14:CB:19:0C:37:1F | - | - | - |
| 10.27.60.224 | 14:CB:19:0B:FA:BB | - | - | - |
| 10.27.60.210 | 14:CB:19:0B:FB:59 | - | - | - |
| 10.27.60.250 | 14:CB:19:0B:FB:A2 | - | - | - |
| 10.27.60.200 | 14:CB:19:0C:07:89 | - | debian | - |
| 10.27.60.201 | 14:CB:19:0C:77:FC | - | - | - |
| 10.27.60.97 | E4:E7:49:51:FB:53 | - | - | - |
| 10.27.60.220 | 14:CB:19:0C:18:AE | - | debian | - |
| 10.27.60.221 | 14:CB:19:0C:52:9B | - | - | - |
| 10.27.60.207 | 14:CB:19:0C:08:B8 | - | - | - |
| 10.27.60.217 | 14:CB:19:0C:82:15 | - | debian | - |
| 10.27.60.199 | 14:CB:19:0B:EB:5C | - | - | - |
| 10.27.60.208 | 14:CB:19:0C:08:E6 | - | debian | - |
| 10.27.60.102 | E4:E7:49:51:F9:06 | - | - | - |
| 10.27.60.205 | 14:CB:19:0C:37:FB | - | debian | - |
| 10.27.60.100 | E4:E7:49:51:FB:7C | - | - | - |
| 10.27.60.204 | 14:CB:19:0C:A8:C4 | - | - | - |
| 10.27.60.215 | 14:CB:19:0C:34:52 | - | debian | - |
| 10.27.60.218 | 14:CB:19:0B:EB:81 | - | - | - |
| 10.27.60.197 | 14:CB:19:0C:47:0C | - | debian | - |
| 10.27.60.226 | 14:CB:19:0B:0B:4C | - | - | - |
| 10.27.60.216 | 14:CB:19:0B:8A:8A | - | - | - |
| 10.27.60.202 | 14:CB:19:0C:08:3D | - | - | - |
| 10.27.60.108 | E4:E7:49:51:F7:D4 | - | debian | - |
| 10.27.60.213 | 14:CB:19:0C:38:6B | - | - | - |
| 10.27.60.211 | 14:CB:19:0C:48:53 | - | - | - |
| 10.27.60.222 | 14:CB:19:0C:C7:8E | - | - | - |
| 10.27.60.223 | 14:CB:19:0C:48:93 | - | - | - |
| 10.27.60.203 | 14:CB:19:0C:28:4D | - | debian | - |
| 10.27.60.198 | 14:CB:19:0C:28:41 | - | debian | - |
| 10.27.60.107 | E4:E7:49:51:F7:4B | - | debian | - |
| 10.27.60.219 | 14:CB:19:0C:57:54 | - | - | - |
| 10.27.60.106 | E4:E7:49:51:FB:D1 | - | debian | - |
| 10.27.60.162 | E4:E7:49:51:FB:3E | - | UB-C-WS281 | - |
| 10.27.60.173 | E4:E7:49:51:F6:EE | - | - | - |
| 10.27.60.110 | E4:E7:49:51:FB:4E | - | - | - |
| 10.27.60.175 | E4:E7:49:51:F8:EB | - | - | - |
| 10.27.60.159 | E4:E7:49:51:F6:FB | - | - | - |
| 10.27.60.158 | E4:E7:49:51:F8:B5 | - | UB-C-WS281 | - |
| 10.27.60.165 | E4:E7:49:51:FC:14 | - | UB-C-WS281 | - |
| 10.27.60.170 | E4:E7:49:51:FB:28 | - | - | - |
| 10.27.60.164 | E4:E7:49:51:F8:2A | - | debian | - |
| 10.27.60.160 | E4:E7:49:51:F5:C1 | - | UB-C-WS281 | - |
| 10.27.60.172 | E4:E7:49:51:F5:B5 | - | UB-C-WS281 | - |
| 10.27.60.169 | E4:E7:49:51:FB:55 | - | UB-C-WS281 | - |
| 10.27.60.138 | E4:E7:49:51:F7:57 | - | UB-C-WS281 | - |
| 10.27.60.139 | E4:E7:49:51:FB:E4 | - | - | - |
| 10.27.60.174 | E4:E7:49:51:F8:75 | - | - | - |
| 10.27.60.147 | E4:E7:49:51:F6:A2 | - | debian | - |
| 10.27.60.252 | E4:E7:49:51:F9:DF | - | - | - |
| 10.27.60.134 | E4:E7:49:51:FA:C3 | - | - | - |
| 10.27.60.157 | E4:E7:49:51:F8:F6 | - | debian | - |
| 10.27.60.156 | E4:E7:49:51:F6:36 | - | - | - |
| 10.27.60.251 | E4:E7:49:51:F6:1A | - | - | - |
| 10.27.60.155 | E4:E7:49:51:FB:62 | - | debian | - |
| 10.27.60.135 | E4:E7:49:51:FA:1B | - | debian | - |
| 10.27.60.148 | E4:E7:49:51:F9:33 | - | - | - |
| 10.27.60.253 | E4:E7:49:51:F8:FA | - | - | - |
| 10.27.60.90 | E4:E7:49:51:F8:01 | 161 | - | - |
| 10.27.60.89 | E4:E7:49:51:F8:F0 | 162 | - | - |
| 10.27.60.80 | E4:E7:49:51:FB:4F | 103 | debian | - |
| 10.27.60.79 | E4:E7:49:51:FA:3A | 104 | debian | - |
| 10.27.60.78 | E4:E7:49:51:F6:E3 | 170 | - | - |
| 10.27.60.84 | E4:E7:49:51:FA:9E | 147 | - | - |
| 10.27.60.81 | E4:E7:49:51:FA:18 | 167 | - | - |
| 10.27.60.87 | E4:E7:49:51:F9:A6 | 121 | - | - |
| 10.27.60.82 | E4:E7:49:51:FA:F7 | 168 | - | - |
| 10.27.60.83 | E4:E7:49:51:FC:0C | 169 | - | - |
| 10.27.60.88 | E4:E7:49:51:F6:9B | 122 | UB-D-WS162 | - |
| 10.27.60.74 | 10:FF:E0:66:70:82 | - | pxeutbk | 1w1d3h25m32s |
| 10.27.60.76 | 14:CB:19:0C:57:C3 | - | debian | 6d20h51m24s |

### Server: fk-8-dhcp_LabA

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.59.50 | D4:61:37:0D:09:28 | - | - | - |
| 10.27.59.22 | 38:F3:AB:B3:CB:30 | - | DESKTOP-SJHOS1C | - |

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

Terdeteksi 97 perangkat baru dengan `MAC address` yang belum pernah tercatat, sementara 121 perangkat mengalami `disconnect`. Jumlah `disconnect` yang signifikan perlu diinvestigasi lebih lanjut untuk memastikan apakah ini disebabkan oleh pemindahan fisik perangkat atau masalah pada `DHCP server` dan `lease` yang tidak valid.

### 🔵 Perangkat Baru Terdeteksi (97 perangkat)

Perangkat yang **pertama kali terlihat** pada tanggal ini (berdasarkan MAC address).

| MAC Address | IP Address | Comment | Hostname | Client ID | Status | Server |
|---|---|---|---|---|---|---|
| 14:CB:19:0B:EB:4A | 10.39.0.184 | Lab2-64 | utbk-os | 1:14:cb:19:b:eb:4a | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:14:B1 | 10.39.0.179 | Lab2-66 | utbk-os | 1:14:cb:19:c:14:b1 | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:14:D6 | 10.39.0.168 | lab3-64 | utbk-os | 1:14:cb:19:c:14:d6 | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:18:78 | 10.39.0.183 | Lab2-63 | utbk-os | 1:14:cb:19:c:18:78 | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:24:C0 | 10.39.0.170 | lab3-66 | utbk-os | 1:14:cb:19:c:24:c0 | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:28:AB | 10.39.0.156 | lab3-63 | utbk-os | 1:14:cb:19:c:28:ab | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:57:B9 | 10.39.0.175 | lab3-62 | utbk-os | 1:14:cb:19:c:57:b9 | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:92:7E | 10.39.0.181 | Lab2-62 | utbk-os | 1:14:cb:19:c:92:7e | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:B7:E1 | 10.39.0.180 | Lab2-61 | utbk-os | 1:14:cb:19:c:b7:e1 | bound | dti-dhcp-lab-tik |
| 14:CB:19:0C:E3:02 | 10.39.0.169 | Lab2-65 | utbk-os | 1:14:cb:19:c:e3:2 | bound | dti-dhcp-lab-tik |
| 20:3A:43:02:68:9F | 10.23.82.107 | - | utbk-os | 1:20:3a:43:2:68:9f | bound | fia-dhcp-2380-lab |
| 38:F3:AB:B3:CB:30 | 10.27.59.22 | - | DESKTOP-SJHOS1C | 1:38:f3:ab:b3:cb:30 | bound | fk-8-dhcp_LabA |
| 40:8D:5C:39:95:17 | 10.28.160.177 | - | utbk-os | 1:40:8d:5c:39:95:17 | bound | fpik-serverlabutbk |
| 40:8D:5C:39:95:19 | 10.28.160.178 | - | utbk-os | 1:40:8d:5c:39:95:19 | bound | fpik-serverlabutbk |
| A0:AD:9F:96:3C:2D | 10.23.82.108 | - | utbk-os | 1:a0:ad:9f:96:3c:2d | bound | fia-dhcp-2380-lab |
| C8:5A:CF:39:0D:BC | 10.39.0.177 | Lab2-55 | utbk-os | 1:c8:5a:cf:39:d:bc | bound | dti-dhcp-lab-tik |
| C8:5A:CF:39:3E:BD | 10.39.0.138 | Lab2-27 | utbk-os | 1:c8:5a:cf:39:3e:bd | bound | dti-dhcp-lab-tik |
| C8:5A:CF:39:9D:79 | 10.39.0.123 | Lab2-18 | utbk-os | 1:c8:5a:cf:39:9d:79 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3A:35:7B | 10.39.0.121 | Lab2-20 | utbk-os | 1:c8:5a:cf:3a:35:7b | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3A:93:40 | 10.39.0.115 | Lab2-26 | utbk-os | 1:c8:5a:cf:3a:93:40 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3A:E2:03 | 10.39.0.89 | Lab2-01 | utbk-os | 1:c8:5a:cf:3a:e2:3 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:0D:A4 | 10.39.0.224 | Lab2-19 | utbk-os | 1:c8:5a:cf:3b:d:a4 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:0D:AF | 10.39.0.117 | Lab2-36 | utbk-os | 1:c8:5a:cf:3b:d:af | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:0D:DE | 10.39.0.178 | Lab2-31 | utbk-os | 1:c8:5a:cf:3b:d:de | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:8C:D9 | 10.39.0.107 | Lab2-10 | utbk-os | 1:c8:5a:cf:3b:8c:d9 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:BE:DF | 10.39.0.146 | Lab2-49 | utbk-os | 1:c8:5a:cf:3b:be:df | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:CD:E4 | 10.39.0.59 | Lab2-32 | utbk-os | 1:c8:5a:cf:3b:cd:e4 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:DC:40 | 10.39.0.158 | Lab2-59 | utbk-os | 1:c8:5a:cf:3b:dc:40 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:DD:8C | 10.39.0.173 | Lab2-54 | utbk-os | 1:c8:5a:cf:3b:dd:8c | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:ED:D8 | 10.39.0.137 | Lab2-30 | utbk-os | 1:c8:5a:cf:3b:ed:d8 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:FC:37 | 10.39.0.109 | Lab2-14 | utbk-os | 1:c8:5a:cf:3b:fc:37 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3B:FC:B9 | 10.39.0.113 | Lab2-16 | utbk-os | 1:c8:5a:cf:3b:fc:b9 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:01:7D | 10.39.0.129 | Lab2-23 | utbk-os | 1:c8:5a:cf:3c:1:7d | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:01:82 | 10.39.0.134 | Lab2-17 | utbk-os | 1:c8:5a:cf:3c:1:82 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:11:4F | 10.39.1.14 | Lab2-57 | utbk-os | 1:c8:5a:cf:3c:11:4f | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:19:A5 | 10.39.0.165 | Lab2-51 | utbk-os | 1:c8:5a:cf:3c:19:a5 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:21:15 | 10.39.0.37 | Lab2-42 | utbk-os | 1:c8:5a:cf:3c:21:15 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:24:6D | 10.39.0.99 | Lab2-13 | utbk-os | 1:c8:5a:cf:3c:24:6d | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:31:0E | 10.39.0.116 | Lab2-21 | utbk-os | 1:c8:5a:cf:3c:31:e | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:31:99 | 10.39.0.157 | Lab2-58 | utbk-os | 1:c8:5a:cf:3c:31:99 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:31:AF | 10.39.0.131 | Lab2-24 | utbk-os | 1:c8:5a:cf:3c:31:af | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:31:DC | 10.39.0.101 | Lab2-11 | utbk-os | 1:c8:5a:cf:3c:31:dc | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:51:29 | 10.39.0.86 | Lab2-04 | utbk-os | 1:c8:5a:cf:3c:51:29 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:51:E9 | 10.39.0.58 | Lab2-60 | utbk-os | 1:c8:5a:cf:3c:51:e9 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:61:95 | 10.39.0.176 | Lab2-50 | utbk-os | 1:c8:5a:cf:3c:61:95 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:67:65 | 10.39.0.174 | Lab2-40 | utbk-os | 1:c8:5a:cf:3c:67:65 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:70:21 | 10.39.0.34 | Lab2-37 | utbk-os | 1:c8:5a:cf:3c:70:21 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:7A:DE | 10.39.0.92 | Lab2-06 | utbk-os | 1:c8:5a:cf:3c:7a:de | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:80:82 | 10.39.0.33 | Lab2-47 | utbk-os | 1:c8:5a:cf:3c:80:82 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:90:DE | 10.39.0.239 | Lab2-38 | utbk-os | 1:c8:5a:cf:3c:90:de | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:98:67 | 10.39.0.159 | Lab2-33 | utbk-os | 1:c8:5a:cf:3c:98:67 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:A9:C9 | 10.39.0.128 | Lab2-35 | utbk-os | 1:c8:5a:cf:3c:a9:c9 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:B8:39 | 10.39.0.122 | Lab2-25 | utbk-os | 1:c8:5a:cf:3c:b8:39 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:B9:88 | 10.39.0.111 | Lab2-15 | utbk-os | 1:c8:5a:cf:3c:b9:88 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:C1:CE | 10.39.0.127 | Lab2-22 | utbk-os | 1:c8:5a:cf:3c:c1:ce | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:C8:58 | 10.39.0.166 | Lab2-43 | utbk-os | 1:c8:5a:cf:3c:c8:58 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:D6:15 | 10.39.0.88 | Lab2-02 | utbk-os | 1:c8:5a:cf:3c:d6:15 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:E1:EB | 10.39.0.90 | Lab2-05 | utbk-os | 1:c8:5a:cf:3c:e1:eb | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:E6:1E | 10.39.0.161 | Lab2-56 | utbk-os | 1:c8:5a:cf:3c:e6:1e | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:E7:E4 | 10.39.0.135 | Lab2-34 | utbk-os | 1:c8:5a:cf:3c:e7:e4 | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:E8:9C | 10.39.0.139 | Lab2-29 | utbk-os | 1:c8:5a:cf:3c:e8:9c | bound | dti-dhcp-lab-tik |
| C8:5A:CF:3C:E9:33 | 10.39.0.145 | Lab2-41 | utbk-os | 1:c8:5a:cf:3c:e9:33 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:81:00 | 10.39.0.155 | Lab1-32 | utbk-os | 1:d4:93:90:18:81:0 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:81:0B | 10.39.0.133 | Lab1-16 | utbk-os | 1:d4:93:90:18:81:b | bound | dti-dhcp-lab-tik |
| D4:93:90:18:85:5E | 10.39.0.106 | Lab1-20 | utbk-os | 1:d4:93:90:18:85:5e | bound | dti-dhcp-lab-tik |
| D4:93:90:18:85:6C | 10.39.0.124 | Lab1-14 | utbk-os | 1:d4:93:90:18:85:6c | bound | dti-dhcp-lab-tik |
| D4:93:90:18:87:0A | 10.39.0.148 | Lab1-27 | utbk-os | 1:d4:93:90:18:87:a | bound | dti-dhcp-lab-tik |
| D4:93:90:18:89:CA | 10.39.0.160 | Lab1-34 | utbk-os | 1:d4:93:90:18:89:ca | bound | dti-dhcp-lab-tik |
| D4:93:90:18:9B:7C | 10.39.0.141 | Lab1-26 | utbk-os | 1:d4:93:90:18:9b:7c | bound | dti-dhcp-lab-tik |
| D4:93:90:18:9E:0A | 10.39.0.103 | Lab1-08 | utbk-os | 1:d4:93:90:18:9e:a | bound | dti-dhcp-lab-tik |
| D4:93:90:18:9F:03 | 10.39.0.104 | Lab1-07 | utbk-os | 1:d4:93:90:18:9f:3 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:A1:05 | 10.39.0.144 | Lab1-23 | utbk-os | 1:d4:93:90:18:a1:5 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:A1:33 | 10.39.0.149 | Lab1-30 | utbk-os | 1:d4:93:90:18:a1:33 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:A4:45 | 10.39.0.93 | Lab1-03 | utbk-os | 1:d4:93:90:18:a4:45 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:A4:F7 | 10.39.0.147 | Lab1-31 | utbk-os | 1:d4:93:90:18:a4:f7 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:A6:4D | 10.39.0.152 | Lab1-33 | utbk-os | 1:d4:93:90:18:a6:4d | bound | dti-dhcp-lab-tik |
| D4:93:90:18:C3:17 | 10.39.0.132 | Lab1-18 | utbk-os | 1:d4:93:90:18:c3:17 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:C4:25 | 10.39.0.142 | Lab1-25 | utbk-os | 1:d4:93:90:18:c4:25 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:C6:78 | 10.39.0.118 | Lab1-19 | utbk-os | 1:d4:93:90:18:c6:78 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:C6:B4 | 10.39.0.140 | Lab1-24 | utbk-os | 1:d4:93:90:18:c6:b4 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:C7:DD | 10.39.0.114 | Lab1-11 | utbk-os | 1:d4:93:90:18:c7:dd | bound | dti-dhcp-lab-tik |
| D4:93:90:18:C9:6D | 10.39.0.97 | Lab1-02 | utbk-os | 1:d4:93:90:18:c9:6d | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CA:23 | 10.39.0.100 | Lab1-01 | utbk-os | 1:d4:93:90:18:ca:23 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CA:33 | 10.39.0.110 | Lab1-12 | utbk-os | 1:d4:93:90:18:ca:33 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CB:86 | 10.39.0.136 | Lab1-17 | utbk-os | 1:d4:93:90:18:cb:86 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CB:AE | 10.39.0.112 | Lab1-21 | utbk-os | 1:d4:93:90:18:cb:ae | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CB:B3 | 10.39.0.105 | Lab1-09 | utbk-os | 1:d4:93:90:18:cb:b3 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CC:CD | 10.39.0.94 | Lab1-10 | utbk-os | 1:d4:93:90:18:cc:cd | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CD:91 | 10.39.0.91 | Lab1-04 | utbk-os | 1:d4:93:90:18:cd:91 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CD:D1 | 10.39.0.164 | Lab1-35 | utbk-os | 1:d4:93:90:18:cd:d1 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CE:25 | 10.39.0.96 | Lab1-05 | utbk-os | 1:d4:93:90:18:ce:25 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CE:2E | 10.39.0.79 | Lab1-22 | utbk-os | 1:d4:93:90:18:ce:2e | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CE:C2 | 10.39.0.102 | Lab1-06 | utbk-os | 1:d4:93:90:18:ce:c2 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:CF:35 | 10.39.0.143 | Lab1-28 | utbk-os | 1:d4:93:90:18:cf:35 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:D0:D5 | 10.39.0.154 | Lab1-29 | utbk-os | 1:d4:93:90:18:d0:d5 | bound | dti-dhcp-lab-tik |
| D4:93:90:18:D0:EC | 10.39.0.130 | Lab1-15 | utbk-os | 1:d4:93:90:18:d0:ec | bound | dti-dhcp-lab-tik |
| D4:93:90:18:D1:2F | 10.39.0.120 | Lab1-13 | utbk-os | 1:d4:93:90:18:d1:2f | bound | dti-dhcp-lab-tik |

### 🔴 Perangkat Disconnect (121 perangkat)

Perangkat yang **tidak terlihat** pada tanggal ini tetapi pernah ada di hari sebelumnya.

| MAC Address | Terakhir Seen | Server Terakhir |
|---|---|---|
| 08:8F:C3:BE:4C:D4 | 20260421 | fisip-serverpoollab |
| 08:8F:C3:BE:4F:D9 | 20260421 | fisip-serverpoollab |
| 14:CB:19:0B:DA:01 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0B:FA:C5 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:18:95 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:18:D0 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:28:07 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:38:64 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:47:0E | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:48:D9 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:57:12 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:72:5E | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:98:BF | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:B6:72 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:B8:36 | 20260421 | dti-dhcp-lab-tik |
| 14:CB:19:0C:D3:33 | 20260421 | dti-dhcp-lab-tik |
| 20:3A:43:02:61:63 | 20260421 | fia-dhcp-2380-lab |
| 84:47:09:19:3F:1D | 20260421 | dti-dhcp-lab-tik |
| 84:47:09:19:41:1F | 20260421 | dti-dhcp-lab-tik |
| 84:47:09:19:43:D9 | 20260421 | dti-dhcp-lab-tik |
| 84:47:09:19:44:20 | 20260421 | dti-dhcp-lab-tik |
| 84:47:09:19:4C:45 | 20260421 | dti-dhcp-lab-tik |
| 8C:32:23:32:30:31 | 20260421 | fia-dhcp-2380-lab |
| 9C:5A:44:8B:11:C5 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8B:4F:3D | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8B:50:4B | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:78:61 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:78:8C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:78:A4 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:78:C8 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:79:1A | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:79:39 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:79:3B | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:79:A8 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:79:BE | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:79:FB | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:1C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:3D | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:67 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:69 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:98 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:A6 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:AF | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7A:FA | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:19 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:1C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:28 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:49 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:53 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:6E | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:B0 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:C5 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7B:FC | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:00 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:14 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:21 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:3A | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:6B | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:7F | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:81 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:A2 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:E7 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7C:FF | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7D:09 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7D:59 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7D:6C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7D:73 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7D:97 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7E:96 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7E:DE | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7F:56 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7F:D6 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:7F:EA | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:49 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:4E | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:76 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:79 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:AC | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:BF | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:DD | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:E0 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:E8 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:ED | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:80:F8 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:37 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:3B | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:4C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:50 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:57 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:AA | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:B8 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:BB | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:BE | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:BF | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:C3 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:D9 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:DC | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:DF | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:E0 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:F3 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:81:FE | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:82:04 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:82:10 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:82:1C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:9E:AD | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:9F:2D | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:9F:57 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:9F:9E | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A0:14 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A2:97 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A2:E2 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A3:06 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A3:42 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A3:71 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A3:B3 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A4:FA | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A5:67 | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8C:A6:2C | 20260421 | dti-dhcp-lab-tik |
| 9C:5A:44:8F:45:1B | 20260421 | dti-dhcp-lab-tik |
| C8:5A:CF:3C:D0:45 | 20260421 | dti-dhcp-lab-tik |
| E0:C7:67:90:8A:7E | 20260421 | dti-dhcp-lab-tik |

---

## 8. 📍 Anomali per Router

Distribusi anomali tersebar pada lima `router` berbeda dengan total 58 perangkat terdampak, namun hanya tiga tingkat keparahan yang tercatat (satu CRITICAL, satu HIGH, dan satu MEDIUM). `Router` `fia-dhcp-2380-lab` menjadi prioritas utama penanganan karena menampung anomali tingkat CRITICAL yang mengindikasikan risiko gangguan layanan paling serius dibandingkan `router` lainnya.

### dti-dhcp-lab-tik (4 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w4d4h44m33s |
| 🔴 CRITICAL | 10.39.0.236 | - | dti-dhcp-lab-tik | Waiting: 2w2d2h58m54s |
| 🔴 HIGH | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w4d4h44m33s |
| 🔴 HIGH | 10.39.0.236 | - | dti-dhcp-lab-tik | Waiting: 2w2d2h58m54s |

### fia-dhcp-2380-lab (22 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h59m59s |
| 🔴 CRITICAL | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h59m56s |
| 🔴 CRITICAL | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h59m34s |
| 🔴 CRITICAL | 10.23.80.32 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h45m9s |
| 🔴 CRITICAL | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h13m11s |
| 🔴 CRITICAL | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h9m42s |
| 🔴 CRITICAL | 10.23.80.27 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w3d3h4m53s |
| 🔴 CRITICAL | 10.23.80.25 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w2d3h15m34s |
| 🔴 CRITICAL | 10.23.80.41 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w6d20h45m19s |
| 🔴 CRITICAL | 10.23.80.37 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w1d1h20m9s |
| 🔴 CRITICAL | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w1d1h16m49s |
| 🔴 HIGH | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h59m59s |
| 🔴 HIGH | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h59m56s |
| 🔴 HIGH | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h59m34s |
| 🔴 HIGH | 10.23.80.32 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h45m9s |
| 🔴 HIGH | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h13m11s |
| 🔴 HIGH | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w6d23h9m42s |
| 🔴 HIGH | 10.23.80.27 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w3d3h4m53s |
| 🔴 HIGH | 10.23.80.25 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w2d3h15m34s |
| 🔴 HIGH | 10.23.80.41 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w6d20h45m19s |
| 🔴 HIGH | 10.23.80.37 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w1d1h20m9s |
| 🔴 HIGH | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w1d1h16m49s |

### fisip-serverpoollab (5 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 10w1d1h46m4s |
| 🔴 CRITICAL | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 10w1d1h45m47s |
| 🔴 CRITICAL | 10.31.16.73 | LAB-B18 | fisip-serverpoollab | Waiting: 1w2d21h26m59s |
| 🔴 HIGH | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 10w1d1h46m4s |
| 🔴 HIGH | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 10w1d1h45m47s |

### fk-1-LAB_Lt.1 (3 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.27.60.176 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 31w2d22h39m11s |
| 🔴 HIGH | 10.27.60.176 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 31w2d22h39m11s |
| 🟡 MEDIUM | 10.27.60.74 | pxeutbk | fk-1-LAB_Lt.1 | Age: 1w1d3h25m32s |

### fpik-serverlabutbk (24 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.28.160.123 | utbk-os | fpik-serverlabutbk | Waiting: 3w2d3h44m51s |
| 🟡 MEDIUM | 10.28.160.121 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m55s |
| 🟡 MEDIUM | 10.28.160.187 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m51s |
| 🟡 MEDIUM | 10.28.160.145 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m39s |
| 🟡 MEDIUM | 10.28.160.122 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m21s |
| 🟡 MEDIUM | 10.28.160.97 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m16s |
| 🟡 MEDIUM | 10.28.160.125 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m10s |
| 🟡 MEDIUM | 10.28.160.82 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m9s |
| 🟡 MEDIUM | 10.28.160.115 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m6s |
| 🟡 MEDIUM | 10.28.160.92 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h45m5s |
| 🟡 MEDIUM | 10.28.160.94 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m51s |
| 🟡 MEDIUM | 10.28.160.116 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m47s |
| 🟡 MEDIUM | 10.28.160.127 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m32s |
| 🟡 MEDIUM | 10.28.160.102 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m31s |
| 🟡 MEDIUM | 10.28.160.109 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m23s |
| 🟡 MEDIUM | 10.28.160.107 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m15s |
| 🟡 MEDIUM | 10.28.160.55 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m4s |
| 🟡 MEDIUM | 10.28.160.108 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m4s |
| 🟡 MEDIUM | 10.28.160.93 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h44m1s |
| 🟡 MEDIUM | 10.28.160.96 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h43m44s |
| 🟡 MEDIUM | 10.28.160.129 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h43m32s |
| 🟡 MEDIUM | 10.28.160.128 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h40m54s |
| 🟡 MEDIUM | 10.28.160.98 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h40m52s |
| 🟡 MEDIUM | 10.28.160.99 | utbk-os | fpik-serverlabutbk | Age: 3w2d3h40m13s |

## 9. ⚠️ ANOMALI TERDETEKSI

Terdapat 18 perangkat dalam status `waiting` yang sudah berlangsung lama, dengan durasi terlama mencapai lebih dari tiga minggu, yang mengindikasikan kegagalan persisten dalam proses `lease` dan kemungkinan perangkat tersebut sudah tidak aktif atau rusak. Kondisi ini harus segera diintervensi dengan menonaktifkan atau menghapus entri `bound` yang menumpuk (24 kasus) serta membersihkan `waiting` yang tidak pernah terlihat lebih dari dua minggu (16 kasus) untuk membebaskan slot di `IP pool` dan mencegah kelelahan alamat di `subnet`. Urgensi tinggi pada anomali `CRITICAL` ini menuntut tindakan segera agar `DHCP server` dapat kembali mengalokasikan `IP address` secara efisien kepada perangkat yang benar-benar aktif.

### 🔴 ANOMALI 1: Perangkat Waiting Sudah Berhari-hari (CRITICAL)

Terdapat **18 perangkat waiting** yang sudah mencoba mendapatkan IP selama lebih dari 1 hari.

| IP | Comment | Hostname | MAC | Durasi |
|---|---|---|---|---|
| 10.27.60.176 | - | UB-C-WS281 | E4:E7:49:51:FB:E6 | 31w2d22h39m11s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 70:F3:95:01:2E:40 | 19w6d23h59m59s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 00:24:7E:0A:83:CE | 19w6d23h59m56s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 00:24:7E:0A:84:0E | 19w6d23h59m34s |
| 10.23.80.32 | LAB-UTBK-28 | LAB-SIM-01 | 00:24:7E:0A:83:C9 | 19w6d23h45m9s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 00:24:7E:0A:84:04 | 19w6d23h13m11s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 00:24:7E:0A:83:E5 | 19w6d23h9m42s |
| 10.23.80.27 | LAB-UTBK-23 | LAB-SIM-01 | 00:24:7E:0A:4B:D1 | 19w3d3h4m53s |
| 10.23.80.25 | LAB-UTBK-21 | LAB-SIM-01 | 00:24:7E:0A:85:C0 | 19w2d3h15m34s |
| 10.23.80.41 | LAB-UTBK-37 | LAB-SIM-01 | 00:24:7E:0A:4C:1D | 18w6d20h45m19s |
| 10.23.80.37 | LAB-UTBK-33 | LAB-SIM-01 | 70:F3:95:01:2E:0D | 18w1d1h20m9s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 00:24:7E:0A:84:21 | 18w1d1h16m49s |
| 10.31.16.79 | - | LAB-B24 | 08:8F:C3:BE:4F:CD | 10w1d1h46m4s |
| 10.31.16.80 | - | LAB-B25 | 08:8F:C3:BE:4F:98 | 10w1d1h45m47s |
| 10.28.160.123 | - | utbk-os | 00:E0:4C:80:21:20 | 3w2d3h44m51s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 28:C9:7A:FC:58:2B | 2w4d4h44m33s |
| 10.39.0.236 | - | - | 80:BC:37:2C:C7:E0 | 2w2d2h58m54s |
| 10.31.16.73 | - | LAB-B18 | 08:8F:C3:BC:10:C8 | 1w2d21h26m59s |

**Rekomendasi:** Cek koneksi fisik dan konfigurasi DHCP client. Jika tidak digunakan, disable entri.

---

### 🔴 ANOMALI 2: Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu (HIGH)

Terdapat **16 perangkat waiting** yang `last-seen` sudah lebih dari 2 minggu.

| IP | Comment | Hostname | Last Seen |
|---|---|---|---|
| 10.27.60.176 | - | UB-C-WS281 | 31w2d22h39m11s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 19w6d23h59m59s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 19w6d23h59m56s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 19w6d23h59m34s |
| 10.23.80.32 | LAB-UTBK-28 | LAB-SIM-01 | 19w6d23h45m9s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 19w6d23h13m11s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 19w6d23h9m42s |
| 10.23.80.27 | LAB-UTBK-23 | LAB-SIM-01 | 19w3d3h4m53s |
| 10.23.80.25 | LAB-UTBK-21 | LAB-SIM-01 | 19w2d3h15m34s |
| 10.23.80.41 | LAB-UTBK-37 | LAB-SIM-01 | 18w6d20h45m19s |
| 10.23.80.37 | LAB-UTBK-33 | LAB-SIM-01 | 18w1d1h20m9s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 18w1d1h16m49s |
| 10.31.16.79 | - | LAB-B24 | 10w1d1h46m4s |
| 10.31.16.80 | - | LAB-B25 | 10w1d1h45m47s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 2w4d4h44m33s |
| 10.39.0.236 | - | - | 2w2d2h58m54s |

**Rekomendasi:** Disable/hapus entri ini untuk bebaskan IP pool.

---

### 🟡 ANOMALI 3: Perangkat Bound Terlalu Lama (> 3 Hari) (MEDIUM)

Terdapat **24 perangkat bound** yang sudah lebih dari 3 hari.

| IP | Comment | Hostname | Age | Expires After |
|---|---|---|---|---|
| 10.28.160.121 | - | utbk-os | 3w2d3h45m55s | 27m35s |
| 10.28.160.187 | - | utbk-os | 3w2d3h45m51s | 27m31s |
| 10.28.160.145 | - | utbk-os | 3w2d3h45m39s | 27m23s |
| 10.28.160.122 | - | utbk-os | 3w2d3h45m21s | 27m27s |
| 10.28.160.97 | - | utbk-os | 3w2d3h45m16s | 27m18s |
| 10.28.160.125 | - | utbk-os | 3w2d3h45m10s | 27m48s |
| 10.28.160.82 | - | utbk-os | 3w2d3h45m9s | 27m49s |
| 10.28.160.115 | - | utbk-os | 3w2d3h45m6s | 27m52s |
| 10.28.160.92 | - | utbk-os | 3w2d3h45m5s | 24m29s |
| 10.28.160.94 | - | utbk-os | 3w2d3h44m51s | 28m16s |
| 10.28.160.116 | - | utbk-os | 3w2d3h44m47s | 28m11s |
| 10.28.160.127 | - | utbk-os | 3w2d3h44m32s | 28m28s |
| 10.28.160.102 | - | utbk-os | 3w2d3h44m31s | 29m1s |
| 10.28.160.109 | - | utbk-os | 3w2d3h44m23s | 29m |
| 10.28.160.107 | - | utbk-os | 3w2d3h44m15s | 29m2s |
| 10.28.160.55 | - | utbk-os | 3w2d3h44m4s | 29m23s |
| 10.28.160.108 | - | utbk-os | 3w2d3h44m4s | 29m30s |
| 10.28.160.93 | - | utbk-os | 3w2d3h44m1s | 29m13s |
| 10.28.160.96 | - | utbk-os | 3w2d3h43m44s | 29m47s |
| 10.28.160.129 | - | utbk-os | 3w2d3h43m32s | 29m25s |
| 10.28.160.128 | - | utbk-os | 3w2d3h40m54s | 25m49s |
| 10.28.160.98 | - | utbk-os | 3w2d3h40m52s | 29m27s |
| 10.28.160.99 | - | utbk-os | 3w2d3h40m13s | 16m57s |
| 10.27.60.74 | - | pxeutbk | 1w1d3h25m32s | 1w4d16h20m34s |

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

*Report generated: 24 April 2026*
