# 📊 Laporan DHCP Lease — 25 April 2026

**Tanggal:** 25 April 2026
**Total Server:** 23
**File Sumber:** 23 file di direktori `output/`
**Perbandingan:** 1818 perangkat hari ini vs 5474 perangkat hari sebelumnya

---

## 🗒️ Ringkasan Eksekutif

Kondisi `DHCP server` menunjukkan pergeseran signifikan hari ini; jumlah perangkat dalam status `bound` turun drastis, sementara yang `waiting` meningkat. Meskipun tidak ada `subnet` yang kritis, terdapat 151 perangkat terdampak oleh tiga anomali berbeda, dengan satu insiden berperingkat CRITICAL. Perubahan besar ini memerlukan investigasi segera pada alokasi `IP address` untuk memitigasi potensi kegagalan layanan. Rekomendasi utama adalah fokus pada analisis akar masalah dari anomali yang mempengaruhi perangkat yang seharusnya dalam status `bound`.

---

## 1. Ringkasan Status

Mayoritas perangkat saat ini berada dalam status `waiting` dengan jumlah yang signifikan, jauh melampaui ambang batas normal yang ditetapkan. Tingginya jumlah perangkat dalam status `waiting` ini menunjukkan bahwa sebagian besar klien kesulitan memperoleh `IP address` dari `DHCP server`. Perlu dilakukan investigasi segera pada infrastruktur `DHCP server` dan potensi masalah pada `pool` alamat.

| Status | Jumlah | Persentase |
|---|---|---|
| **Bound** | 806 | 44.3% |
| **Waiting** | 1012 | 55.7% |
| **Disabled (X)** | 0 | 0.0% |
| **Total** | **1818** | 100% |

## 2. 📈 Tren Historis (7 Hari Terakhir)

Tren `bound` menunjukkan fluktuasi signifikan, dengan penurunan tajam dari 1667 menjadi 806 pada 25 April. Peningkatan `waiting` yang signifikan pada 25 April, naik dari 154 menjadi 1012, mungkin terkait dengan perubahan status `lease` atau beban pada `DHCP server`. Perubahan ini perlu dipantau karena menunjukkan adanya peningkatan permintaan atau masalah alokasi `IP address`.

| Tanggal | Bound | Waiting | Total |
|---|---|---|---|
| 21 April 2026 | 1666 | 168 | 1834 |
| 22 April 2026 | 858 | 961 | 1819 |
| 24 April 2026 | 1667 | 154 | 1821 |
| 25 April 2026 | 806 | 1012 | 1818 |

## 3. 📊 Utilisasi IP Pool

Analisis utilisasi menunjukkan bahwa tidak ada `subnet` yang kritis. Namun, `subnet` `10.39.0.0/24` berada dalam kondisi waspada karena utilisasinya mencapai sekitar 80%. Risiko kekurangan `IP address` belum mendesak, tetapi perlu dipantau karena mendekati batas waspada. Saya sarankan memonitor tren penggunaan pada `subnet` tersebut dan menyiapkan rencana ekspansi `pool` jika utilisasi terus meningkat.

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
| Bound + UTBK-OS | 605 |
| Bound + Other (non-UTBK) | 201 |
| **Total UTBK-OS** | **605** |

> **Rasio UTBK-OS terhadap Bound:** 75.1% (605 dari 806 perangkat bound adalah UTBK-OS)

## 5. Ringkasan per Server DHCP

Distribusi beban antar `DHCP server` tidak merata; beberapa server menunjukkan jumlah `bound` perangkat yang sangat tinggi, sementara yang lain memiliki beban `waiting` yang signifikan. `fk-1-LAB_Lt.1` menangani jumlah `bound` tertinggi, namun `dti-dhcp-lab-tik` dan `fia-dhcp-2380-lab` menunjukkan jumlah `waiting` yang paling banyak. Perlu ditinjau ulang alokasi `pool` dan potensi penyesuaian pada `router` yang melayani server-server tersebut.

| Server | Bound | Waiting | Disabled | Total | UTBK-OS | Other |
|---|---|---|---|---|---|---|
| dti-dhcp-lab-tik | 41 | 232 | 0 | 273 | 38 | 3 |
| fapet-network-Lab | 18 | 5 | 0 | 23 | 18 | 0 |
| feb-CBT | 74 | 60 | 0 | 134 | 74 | 0 |
| fh-lab | 4 | 64 | 0 | 68 | 4 | 0 |
| fia-dhcp-2380-lab | 5 | 131 | 0 | 136 | 2 | 3 |
| fib-server-lab | 15 | 33 | 0 | 48 | 13 | 2 |
| filkom-G1.2-vlan3498 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.3-vlan3495 | 0 | 26 | 0 | 26 | 0 | 0 |
| filkom-G1.4-vlan3496 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.5-vlan3499 | 26 | 0 | 0 | 26 | 26 | 0 |
| filkom-G1.6-vlan3497 | 26 | 0 | 0 | 26 | 26 | 0 |
| fisip-serverpoollab | 0 | 53 | 0 | 53 | 0 | 0 |
| fk-1-LAB_Lt.1 | 168 | 5 | 0 | 173 | 0 | 168 |
| fk-8-dhcp_LabA | 115 | 15 | 0 | 130 | 114 | 1 |
| fk-8-dhcp_LabB | 138 | 5 | 0 | 143 | 137 | 1 |
| fk-8-dhcp_LabC | 43 | 38 | 0 | 81 | 27 | 16 |
| fkg-dhcp2 | 28 | 56 | 0 | 84 | 21 | 7 |
| fp-lab | 0 | 82 | 0 | 82 | 0 | 0 |
| fpik-serverlabutbk | 0 | 60 | 0 | 60 | 0 | 0 |
| ft-dekanat-Lab-66-pimp | 0 | 57 | 0 | 57 | 0 | 0 |
| ft-gbe-Lab-67-Admin | 0 | 29 | 0 | 29 | 0 | 0 |
| ftp-dhcp7 | 41 | 18 | 0 | 59 | 41 | 0 |
| vokasi-3508-serverpoollab | 12 | 43 | 0 | 55 | 12 | 0 |

## 6. Perangkat Bound Non-UTBK-OS

### Server: dti-dhcp-lab-tik

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.39.0.238 | 94:3F:C2:87:B2:E8 | sw-lab-4-barat-belakang | sw-grl-4-lab3-barat-belakang | - |
| 10.39.0.9 | E8:F7:24:17:EC:F0 | - | sw-grl-3-tik-lab1-atas | - |
| 10.39.0.82 | 28:C9:7A:FC:5C:63 | sw-Lab4-selatan | H3C-fc5c63 | 5d59m9s |

### Server: fia-dhcp-2380-lab

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.23.82.32 | 30:9C:23:C1:62:17 | - | DESKTOP-UTR5SS5 | - |
| 10.23.82.110 | 8C:85:C1:B5:A9:CE | - | - | - |
| 10.23.82.107 | F8:46:1C:A1:60:9B | - | - | - |

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
| 10.27.60.243 | 14:CB:19:0B:DB:8E | - | debian | - |
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
| 10.27.60.74 | 10:FF:E0:66:70:82 | - | pxeutbk | 1w2d6h44m52s |
| 10.27.60.76 | 14:CB:19:0C:57:C3 | - | debian | 1w1d10m44s |

### Server: fk-8-dhcp_LabA

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.59.50 | D4:61:37:0D:09:28 | - | - | - |

### Server: fk-8-dhcp_LabB

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.57.42 | EC:8E:B5:D7:AA:C9 | - | UB-B-WS178 | - |

### Server: fk-8-dhcp_LabC

| IP Address | MAC Address | Comment | Hostname | Age |
|---|---|---|---|---|
| 10.27.58.142 | D0:50:99:75:5F:C4 | - | - | - |
| 10.27.58.187 | D0:50:99:72:B8:47 | - | UB-D-WS353 | - |
| 10.27.58.39 | D0:50:99:72:B7:72 | - | UB-D-WS354 | - |
| 10.27.58.54 | E0:69:95:DD:30:85 | - | UB-D-WS352 | - |
| 10.27.58.127 | 00:FD:45:18:02:40 | - | - | - |
| 10.27.58.136 | D0:50:99:72:B7:C3 | - | - | - |
| 10.27.58.34 | D0:50:99:75:61:0C | - | UB-D-WS355 | - |
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
| 10.36.16.165 | E4:E7:49:51:F7:85 | - | fkg18 | - |
| 10.36.16.177 | E0:D5:5E:16:50:4D | - | DESKTOP-36KP9AD | - |

> Perangkat non-UTBK adalah **switch infrastructure** dan perangkat lainnya.

## 7. 📡 Perangkat Baru & Disconnect

Ditemukan satu perangkat baru yang terdeteksi hari ini. Terdapat juga dua belas puluh dua perangkat yang statusnya `disconnect`. Jumlah perangkat yang terputus ini cukup signifikan dan memerlukan investigasi untuk memastikan tidak ada masalah konektivitas atau potensi aktivitas yang tidak wajar.

### 🔵 Perangkat Baru Terdeteksi (1 perangkat)

Perangkat yang **pertama kali terlihat** pada tanggal ini (berdasarkan MAC address).

| MAC Address | IP Address | Comment | Hostname | Client ID | Status | Server |
|---|---|---|---|---|---|---|
| F8:46:1C:A1:60:9B | 10.23.82.107 | - | - | 1:f8:46:1c:a1:60:9b | bound | fia-dhcp-2380-lab |

### 🔴 Perangkat Disconnect (122 perangkat)

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
| 20:3A:43:02:68:9F | 20260424 | fia-dhcp-2380-lab |
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

Terdapat total 151 anomali yang terdistribusi pada tujuh `router` berbeda. Perhatian utama harus difokuskan pada `fia-dhcp-2380-lab` karena mencatat jumlah anomali tertinggi, diikuti oleh `vokasi-3508-serverpoollab`.

### dti-dhcp-lab-tik (27 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w5d8h3m53s |
| 🔴 CRITICAL | 10.39.0.236 | - | dti-dhcp-lab-tik | Waiting: 2w3d6h18m14s |
| 🔴 CRITICAL | 10.39.0.7 | - | dti-dhcp-lab-tik | Waiting: 2w3d3h23m26s |
| 🔴 CRITICAL | 10.39.0.64 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h26m8s |
| 🔴 CRITICAL | 10.39.0.45 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h25m55s |
| 🔴 CRITICAL | 10.39.0.65 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m26s |
| 🔴 CRITICAL | 10.39.0.75 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m24s |
| 🔴 CRITICAL | 10.39.0.17 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m16s |
| 🔴 CRITICAL | 10.39.0.11 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m16s |
| 🔴 CRITICAL | 10.39.0.66 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m11s |
| 🔴 CRITICAL | 10.39.0.67 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m8s |
| 🔴 CRITICAL | 10.39.0.69 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m3s |
| 🔴 CRITICAL | 10.39.0.70 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m3s |
| 🔴 CRITICAL | 10.39.0.55 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m2s |
| 🔴 CRITICAL | 10.39.0.46 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m1s |
| 🔴 CRITICAL | 10.39.0.16 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h24m1s |
| 🔴 CRITICAL | 10.39.0.71 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h23m59s |
| 🔴 CRITICAL | 10.39.0.72 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h23m49s |
| 🔴 CRITICAL | 10.39.0.73 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h23m47s |
| 🔴 CRITICAL | 10.39.0.74 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h23m34s |
| 🔴 CRITICAL | 10.39.0.76 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h22m31s |
| 🔴 CRITICAL | 10.39.0.77 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h18m36s |
| 🔴 CRITICAL | 10.39.0.56 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h16m1s |
| 🔴 CRITICAL | 10.39.0.78 | utbk-os | dti-dhcp-lab-tik | Waiting: 1w1d7h14m27s |
| 🔴 HIGH | 10.39.0.42 | H3C-fc582b | dti-dhcp-lab-tik | Waiting: 2w5d8h3m53s |
| 🔴 HIGH | 10.39.0.236 | - | dti-dhcp-lab-tik | Waiting: 2w3d6h18m14s |
| 🔴 HIGH | 10.39.0.7 | - | dti-dhcp-lab-tik | Waiting: 2w3d3h23m26s |

### fia-dhcp-2380-lab (40 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.23.80.6 | DESKTOP-C75KJDC | fia-dhcp-2380-lab | Waiting: 21w2d3h23m53s |
| 🔴 CRITICAL | 10.23.80.43 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h50m28s |
| 🔴 CRITICAL | 10.23.80.44 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h50m8s |
| 🔴 CRITICAL | 10.23.80.36 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m45s |
| 🔴 CRITICAL | 10.23.80.38 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m39s |
| 🔴 CRITICAL | 10.23.80.40 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m29s |
| 🔴 CRITICAL | 10.23.80.42 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m22s |
| 🔴 CRITICAL | 10.23.80.39 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h11m19s |
| 🔴 CRITICAL | 10.23.80.34 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m26s |
| 🔴 CRITICAL | 10.23.80.31 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m19s |
| 🔴 CRITICAL | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m18s |
| 🔴 CRITICAL | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m15s |
| 🔴 CRITICAL | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h18m53s |
| 🔴 CRITICAL | 10.23.80.32 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h4m28s |
| 🔴 CRITICAL | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d2h32m31s |
| 🔴 CRITICAL | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d2h29m1s |
| 🔴 CRITICAL | 10.23.80.27 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d6h24m12s |
| 🔴 CRITICAL | 10.23.80.25 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w3d6h34m53s |
| 🔴 CRITICAL | 10.23.80.37 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w2d4h39m28s |
| 🔴 CRITICAL | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w2d4h36m8s |
| 🔴 HIGH | 10.23.80.6 | DESKTOP-C75KJDC | fia-dhcp-2380-lab | Waiting: 21w2d3h23m53s |
| 🔴 HIGH | 10.23.80.43 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h50m28s |
| 🔴 HIGH | 10.23.80.44 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h50m8s |
| 🔴 HIGH | 10.23.80.36 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m45s |
| 🔴 HIGH | 10.23.80.38 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m39s |
| 🔴 HIGH | 10.23.80.40 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m29s |
| 🔴 HIGH | 10.23.80.42 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h45m22s |
| 🔴 HIGH | 10.23.80.39 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d7h11m19s |
| 🔴 HIGH | 10.23.80.34 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m26s |
| 🔴 HIGH | 10.23.80.31 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m19s |
| 🔴 HIGH | 10.23.80.30 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m18s |
| 🔴 HIGH | 10.23.80.28 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h19m15s |
| 🔴 HIGH | 10.23.80.33 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h18m53s |
| 🔴 HIGH | 10.23.80.32 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d3h4m28s |
| 🔴 HIGH | 10.23.80.35 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d2h32m31s |
| 🔴 HIGH | 10.23.80.29 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 20w1d2h29m1s |
| 🔴 HIGH | 10.23.80.27 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w4d6h24m12s |
| 🔴 HIGH | 10.23.80.25 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 19w3d6h34m53s |
| 🔴 HIGH | 10.23.80.37 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w2d4h39m28s |
| 🔴 HIGH | 10.23.80.26 | LAB-SIM-01 | fia-dhcp-2380-lab | Waiting: 18w2d4h36m8s |

### fib-server-lab (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.32.8.100 | DESKTOP-14IMVL4 | fib-server-lab | Waiting: 12w6d23h19m37s |
| 🔴 HIGH | 10.32.8.100 | DESKTOP-14IMVL4 | fib-server-lab | Waiting: 12w6d23h19m37s |

### fisip-serverpoollab (52 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.31.16.47 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h15m2s |
| 🔴 CRITICAL | 10.31.16.48 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h13m8s |
| 🔴 CRITICAL | 10.31.16.50 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h12m20s |
| 🔴 CRITICAL | 10.31.16.49 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h11m24s |
| 🔴 CRITICAL | 10.31.16.52 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h11m19s |
| 🔴 CRITICAL | 10.31.16.54 | utbk-pc-disabilitas02 | fisip-serverpoollab | Waiting: 23w1d7h7m43s |
| 🔴 CRITICAL | 10.31.16.55 | LAB-A25 | fisip-serverpoollab | Waiting: 23w1d7h7m43s |
| 🔴 CRITICAL | 10.31.16.43 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h4m16s |
| 🔴 CRITICAL | 10.31.16.31 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m51s |
| 🔴 CRITICAL | 10.31.16.32 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m49s |
| 🔴 CRITICAL | 10.31.16.33 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m48s |
| 🔴 CRITICAL | 10.31.16.34 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m46s |
| 🔴 CRITICAL | 10.31.16.35 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m44s |
| 🔴 CRITICAL | 10.31.16.36 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m42s |
| 🔴 CRITICAL | 10.31.16.37 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m40s |
| 🔴 CRITICAL | 10.31.16.38 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m37s |
| 🔴 CRITICAL | 10.31.16.39 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m36s |
| 🔴 CRITICAL | 10.31.16.40 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m36s |
| 🔴 CRITICAL | 10.31.16.41 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m34s |
| 🔴 CRITICAL | 10.31.16.42 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m33s |
| 🔴 CRITICAL | 10.31.16.51 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h3m31s |
| 🔴 CRITICAL | 10.31.16.56 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m33s |
| 🔴 CRITICAL | 10.31.16.57 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m30s |
| 🔴 CRITICAL | 10.31.16.58 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m25s |
| 🔴 CRITICAL | 10.31.16.60 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m23s |
| 🔴 CRITICAL | 10.31.16.61 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m21s |
| 🔴 CRITICAL | 10.31.16.59 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m21s |
| 🔴 CRITICAL | 10.31.16.67 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m18s |
| 🔴 CRITICAL | 10.31.16.62 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m17s |
| 🔴 CRITICAL | 10.31.16.63 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m15s |
| 🔴 CRITICAL | 10.31.16.66 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m14s |
| 🔴 CRITICAL | 10.31.16.65 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m13s |
| 🔴 CRITICAL | 10.31.16.64 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m11s |
| 🔴 CRITICAL | 10.31.16.69 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m10s |
| 🔴 CRITICAL | 10.31.16.72 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m9s |
| 🔴 CRITICAL | 10.31.16.70 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m8s |
| 🔴 CRITICAL | 10.31.16.73 | LAB-B18 | fisip-serverpoollab | Waiting: 23w1d7h2m6s |
| 🔴 CRITICAL | 10.31.16.71 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m5s |
| 🔴 CRITICAL | 10.31.16.77 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m3s |
| 🔴 CRITICAL | 10.31.16.76 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h2m1s |
| 🔴 CRITICAL | 10.31.16.75 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h1m59s |
| 🔴 CRITICAL | 10.31.16.74 | utbk-os | fisip-serverpoollab | Waiting: 23w1d7h1m54s |
| 🔴 CRITICAL | 10.31.16.46 | utbk-os | fisip-serverpoollab | Waiting: 23w1d6h57m6s |
| 🔴 CRITICAL | 10.31.16.45 | utbk-os | fisip-serverpoollab | Waiting: 23w1d6h57m5s |
| 🔴 CRITICAL | 10.31.16.44 | utbk-os | fisip-serverpoollab | Waiting: 23w1d6h51m25s |
| 🔴 CRITICAL | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 23w1d6h50m3s |
| 🔴 CRITICAL | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 23w1d6h49m55s |
| 🔴 CRITICAL | 10.31.16.68 | utbk-os | fisip-serverpoollab | Waiting: 23w1d6h46m42s |
| 🔴 CRITICAL | 10.31.16.53 | utbk-pc-disabilitas01 | fisip-serverpoollab | Waiting: 23w1d6h41m3s |
| 🔴 HIGH | 10.31.16.79 | LAB-B24 | fisip-serverpoollab | Waiting: 10w2d5h5m24s |
| 🔴 HIGH | 10.31.16.80 | LAB-B25 | fisip-serverpoollab | Waiting: 10w2d5h5m7s |
| 🔴 HIGH | 10.31.16.55 | LAB-A25 | fisip-serverpoollab | Waiting: 10w2d3h46m49s |

### fk-1-LAB_Lt.1 (6 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.27.60.176 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 31w4d1h58m30s |
| 🔴 CRITICAL | 10.27.60.152 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 1w1d8h53m26s |
| 🔴 CRITICAL | 10.27.60.154 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 1w1d8h52m55s |
| 🔴 CRITICAL | 10.27.60.161 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 1w1d8h52m37s |
| 🔴 HIGH | 10.27.60.176 | UB-C-WS281 | fk-1-LAB_Lt.1 | Waiting: 31w4d1h58m30s |
| 🟡 MEDIUM | 10.27.60.74 | pxeutbk | fk-1-LAB_Lt.1 | Age: 1w2d6h44m52s |

### fpik-serverlabutbk (22 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.28.160.121 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h5m15s |
| 🔴 CRITICAL | 10.28.160.187 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h5m11s |
| 🔴 CRITICAL | 10.28.160.145 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m59s |
| 🔴 CRITICAL | 10.28.160.122 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m41s |
| 🔴 CRITICAL | 10.28.160.97 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m36s |
| 🔴 CRITICAL | 10.28.160.125 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m30s |
| 🔴 CRITICAL | 10.28.160.82 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m29s |
| 🔴 CRITICAL | 10.28.160.115 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m26s |
| 🔴 CRITICAL | 10.28.160.92 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m25s |
| 🔴 CRITICAL | 10.28.160.123 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m11s |
| 🔴 CRITICAL | 10.28.160.94 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m11s |
| 🔴 CRITICAL | 10.28.160.116 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h4m7s |
| 🔴 CRITICAL | 10.28.160.127 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m52s |
| 🔴 CRITICAL | 10.28.160.102 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m51s |
| 🔴 CRITICAL | 10.28.160.109 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m43s |
| 🔴 CRITICAL | 10.28.160.107 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m35s |
| 🔴 CRITICAL | 10.28.160.55 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m24s |
| 🔴 CRITICAL | 10.28.160.108 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m24s |
| 🔴 CRITICAL | 10.28.160.93 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m21s |
| 🔴 CRITICAL | 10.28.160.96 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h3m4s |
| 🔴 CRITICAL | 10.28.160.129 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d7h2m52s |
| 🔴 CRITICAL | 10.28.160.99 | utbk-os | fpik-serverlabutbk | Waiting: 3w3d6h59m33s |

### vokasi-3508-serverpoollab (2 anomali)

| Status | IP | Host-name | Active-Server | Detail |
|---|---|---|---|---|
| 🔴 CRITICAL | 10.35.80.83 | 555606b | vokasi-3508-serverpoollab | Waiting: 449w1d13h7m11s |
| 🔴 HIGH | 10.35.80.83 | 555606b | vokasi-3508-serverpoollab | Waiting: 449w1d13h7m11s |

## 9. ⚠️ ANOMALI TERDETEKSI

Terdapat tiga anomali utama yang perlu ditangani. Pertama, ada perangkat yang statusnya `waiting` sudah sangat lama (lebih dari 449 minggu), yang mengindikasikan kegagalan koneksi permanen dan harus segera ditinjau. Kedua, ada perangkat `waiting` yang tidak terlihat selama lebih dari dua minggu, yang memerlukan verifikasi status fisik. Ketiga, satu perangkat yang `bound` sudah terlalu lama (lebih dari tiga hari) dan perlu diperiksa apakah masih aktif atau perlu di-`disabled`.

### 🔴 ANOMALI 1: Perangkat Waiting Sudah Berhari-hari (CRITICAL)

Terdapat **121 perangkat waiting** yang sudah mencoba mendapatkan IP selama lebih dari 1 hari.

| IP | Comment | Hostname | MAC | Durasi |
|---|---|---|---|---|
| 10.35.80.83 | BACKUP | 555606b | 78:45:C4:07:9E:E9 | 449w1d13h7m11s |
| 10.27.60.176 | - | UB-C-WS281 | E4:E7:49:51:FB:E6 | 31w4d1h58m30s |
| 10.31.16.47 | - | utbk-os | 08:8F:C3:BE:4E:D4 | 23w1d7h15m2s |
| 10.31.16.48 | - | utbk-os | 08:8F:C3:BE:4C:A5 | 23w1d7h13m8s |
| 10.31.16.50 | - | utbk-os | 08:8F:C3:BE:4F:1B | 23w1d7h12m20s |
| 10.31.16.49 | - | utbk-os | 08:8F:C3:BE:4F:EE | 23w1d7h11m24s |
| 10.31.16.52 | - | utbk-os | 08:8F:C3:BE:50:06 | 23w1d7h11m19s |
| 10.31.16.54 | laptop | utbk-pc-disabilitas02 | D4:93:90:18:C3:6B | 23w1d7h7m43s |
| 10.31.16.55 | - | LAB-A25 | 08:8F:C3:BE:4E:4D | 23w1d7h7m43s |
| 10.31.16.43 | - | utbk-os | 08:8F:C3:BE:4C:ED | 23w1d7h4m16s |
| 10.31.16.31 | - | utbk-os | 08:8F:C3:BE:4D:8E | 23w1d7h3m51s |
| 10.31.16.32 | - | utbk-os | 08:8F:C3:BE:4F:26 | 23w1d7h3m49s |
| 10.31.16.33 | - | utbk-os | 08:8F:C3:BE:51:F3 | 23w1d7h3m48s |
| 10.31.16.34 | - | utbk-os | 08:8F:C3:BE:4F:C5 | 23w1d7h3m46s |
| 10.31.16.35 | - | utbk-os | 08:8F:C3:BE:4F:A0 | 23w1d7h3m44s |
| 10.31.16.36 | - | utbk-os | 08:8F:C3:BE:4F:7A | 23w1d7h3m42s |
| 10.31.16.37 | - | utbk-os | 08:8F:C3:BE:4F:D4 | 23w1d7h3m40s |
| 10.31.16.38 | - | utbk-os | 08:8F:C3:BE:4C:26 | 23w1d7h3m37s |
| 10.31.16.39 | - | utbk-os | 08:8F:C3:BE:4F:BC | 23w1d7h3m36s |
| 10.31.16.40 | - | utbk-os | 08:8F:C3:BE:4E:FA | 23w1d7h3m36s |
| 10.31.16.41 | - | utbk-os | 08:8F:C3:BE:4F:89 | 23w1d7h3m34s |
| 10.31.16.42 | - | utbk-os | 08:8F:C3:BE:4E:F6 | 23w1d7h3m33s |
| 10.31.16.51 | - | utbk-os | 08:8F:C3:BE:4F:52 | 23w1d7h3m31s |
| 10.31.16.56 | - | utbk-os | 08:8F:C3:BE:4D:24 | 23w1d7h2m33s |
| 10.31.16.57 | - | utbk-os | 08:8F:C3:BD:E4:DC | 23w1d7h2m30s |
| 10.31.16.58 | - | utbk-os | 08:8F:C3:BE:4F:BE | 23w1d7h2m25s |
| 10.31.16.60 | - | utbk-os | 08:8F:C3:BE:4C:EC | 23w1d7h2m23s |
| 10.31.16.61 | - | utbk-os | 08:8F:C3:BE:4F:A1 | 23w1d7h2m21s |
| 10.31.16.59 | - | utbk-os | 08:8F:C3:BE:50:BB | 23w1d7h2m21s |
| 10.31.16.67 | - | utbk-os | 08:8F:C3:BE:4F:D8 | 23w1d7h2m18s |
| 10.31.16.62 | - | utbk-os | 08:8F:C3:BE:4D:A2 | 23w1d7h2m17s |
| 10.31.16.63 | - | utbk-os | 08:8F:C3:BE:4F:BD | 23w1d7h2m15s |
| 10.31.16.66 | - | utbk-os | 08:8F:C3:BE:4F:B8 | 23w1d7h2m14s |
| 10.31.16.65 | - | utbk-os | 08:8F:C3:BE:51:F2 | 23w1d7h2m13s |
| 10.31.16.64 | - | utbk-os | 08:8F:C3:BE:4F:95 | 23w1d7h2m11s |
| 10.31.16.69 | - | utbk-os | 08:8F:C3:BE:4D:1B | 23w1d7h2m10s |
| 10.31.16.72 | - | utbk-os | 08:8F:C3:BE:4B:23 | 23w1d7h2m9s |
| 10.31.16.70 | - | utbk-os | 08:8F:C3:BE:4F:7B | 23w1d7h2m8s |
| 10.31.16.73 | - | LAB-B18 | 08:8F:C3:BC:10:C8 | 23w1d7h2m6s |
| 10.31.16.71 | - | utbk-os | 08:8F:C3:BE:4E:C1 | 23w1d7h2m5s |
| 10.31.16.77 | - | utbk-os | 08:8F:C3:BE:4C:CB | 23w1d7h2m3s |
| 10.31.16.76 | - | utbk-os | 08:8F:C3:BE:4E:C7 | 23w1d7h2m1s |
| 10.31.16.75 | - | utbk-os | 08:8F:C3:BE:4C:D5 | 23w1d7h1m59s |
| 10.31.16.74 | - | utbk-os | 08:8F:C3:BE:4F:01 | 23w1d7h1m54s |
| 10.31.16.46 | - | utbk-os | 08:8F:C3:BE:4E:FD | 23w1d6h57m6s |
| 10.31.16.45 | - | utbk-os | 08:8F:C3:BE:4F:6D | 23w1d6h57m5s |
| 10.31.16.44 | - | utbk-os | 08:8F:C3:BE:4F:84 | 23w1d6h51m25s |
| 10.31.16.79 | - | LAB-B24 | 08:8F:C3:BE:4F:CD | 23w1d6h50m3s |
| 10.31.16.80 | - | LAB-B25 | 08:8F:C3:BE:4F:98 | 23w1d6h49m55s |
| 10.31.16.68 | - | utbk-os | 08:8F:C3:BE:4F:B2 | 23w1d6h46m42s |
| 10.31.16.53 | laptop | utbk-pc-disabilitas01 | D4:93:90:18:D1:A7 | 23w1d6h41m3s |
| 10.23.80.6 | LAB-UTBK-2 | DESKTOP-C75KJDC | E4:E7:49:51:FA:F8 | 21w2d3h23m53s |
| 10.23.80.43 | LAB-UTBK-39 | LAB-SIM-01 | 70:F3:95:01:2D:78 | 20w1d7h50m28s |
| 10.23.80.44 | LAB-UTBK-40 | LAB-SIM-01 | 00:24:7E:0A:85:C1 | 20w1d7h50m8s |
| 10.23.80.36 | LAB-UTBK-32 | LAB-SIM-01 | 00:24:7E:0A:85:42 | 20w1d7h45m45s |
| 10.23.80.38 | LAB-UTBK-34 | LAB-SIM-01 | 00:24:7E:0A:84:33 | 20w1d7h45m39s |
| 10.23.80.40 | LAB-UTBK-36 | LAB-SIM-01 | 00:24:7E:0A:84:7A | 20w1d7h45m29s |
| 10.23.80.42 | LAB-UTBK-38 | LAB-SIM-01 | 00:24:7E:0A:83:EC | 20w1d7h45m22s |
| 10.23.80.39 | LAB-UTBK-35 | LAB-SIM-01 | 00:24:7E:0A:4C:42 | 20w1d7h11m19s |
| 10.23.80.34 | LAB-UTBK-30 | LAB-SIM-01 | 00:10:C6:B0:E1:26 | 20w1d3h19m26s |
| 10.23.80.31 | LAB-UTBK-27 | LAB-SIM-01 | 00:10:C6:B0:E0:92 | 20w1d3h19m19s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 70:F3:95:01:2E:40 | 20w1d3h19m18s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 00:24:7E:0A:83:CE | 20w1d3h19m15s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 00:24:7E:0A:84:0E | 20w1d3h18m53s |
| 10.23.80.32 | LAB-UTBK-28 | LAB-SIM-01 | 00:24:7E:0A:83:C9 | 20w1d3h4m28s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 00:24:7E:0A:84:04 | 20w1d2h32m31s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 00:24:7E:0A:83:E5 | 20w1d2h29m1s |
| 10.23.80.27 | LAB-UTBK-23 | LAB-SIM-01 | 00:24:7E:0A:4B:D1 | 19w4d6h24m12s |
| 10.23.80.25 | LAB-UTBK-21 | LAB-SIM-01 | 00:24:7E:0A:85:C0 | 19w3d6h34m53s |
| 10.23.80.37 | LAB-UTBK-33 | LAB-SIM-01 | 70:F3:95:01:2E:0D | 18w2d4h39m28s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 00:24:7E:0A:84:21 | 18w2d4h36m8s |
| 10.32.8.100 | - | DESKTOP-14IMVL4 | 8C:EC:4B:B8:5E:65 | 12w6d23h19m37s |
| 10.28.160.121 | - | utbk-os | 00:E0:4C:80:21:8E | 3w3d7h5m15s |
| 10.28.160.187 | - | utbk-os | 00:E0:4C:80:21:63 | 3w3d7h5m11s |
| 10.28.160.145 | - | utbk-os | 5C:92:5E:D3:25:A3 | 3w3d7h4m59s |
| 10.28.160.122 | - | utbk-os | 00:E0:4C:80:21:3D | 3w3d7h4m41s |
| 10.28.160.97 | - | utbk-os | 00:E0:4C:80:1D:02 | 3w3d7h4m36s |
| 10.28.160.125 | - | utbk-os | 00:E0:4C:80:1C:D4 | 3w3d7h4m30s |
| 10.28.160.82 | - | utbk-os | 00:E0:4C:80:1C:7E | 3w3d7h4m29s |
| 10.28.160.115 | - | utbk-os | 00:E0:4C:80:21:D5 | 3w3d7h4m26s |
| 10.28.160.92 | - | utbk-os | 00:E0:4C:80:21:77 | 3w3d7h4m25s |
| 10.28.160.123 | - | utbk-os | 00:E0:4C:80:21:20 | 3w3d7h4m11s |
| 10.28.160.94 | - | utbk-os | 00:E0:4C:80:21:34 | 3w3d7h4m11s |
| 10.28.160.116 | - | utbk-os | 5C:92:5E:D3:25:08 | 3w3d7h4m7s |
| 10.28.160.127 | - | utbk-os | 5C:92:5E:D3:22:77 | 3w3d7h3m52s |
| 10.28.160.102 | - | utbk-os | 5C:92:5E:D3:26:AE | 3w3d7h3m51s |
| 10.28.160.109 | - | utbk-os | 00:E0:4C:80:21:DA | 3w3d7h3m43s |
| 10.28.160.107 | - | utbk-os | 00:E0:4C:80:1C:A4 | 3w3d7h3m35s |
| 10.28.160.55 | - | utbk-os | 00:E0:4C:80:21:4B | 3w3d7h3m24s |
| 10.28.160.108 | - | utbk-os | 5C:92:5E:D3:25:09 | 3w3d7h3m24s |
| 10.28.160.93 | - | utbk-os | 00:E0:4C:80:1D:22 | 3w3d7h3m21s |
| 10.28.160.96 | - | utbk-os | 5C:92:5E:D3:25:0B | 3w3d7h3m4s |
| 10.28.160.129 | - | utbk-os | 00:E0:4C:80:1C:8D | 3w3d7h2m52s |
| 10.28.160.99 | - | utbk-os | 00:E0:4C:80:21:5A | 3w3d6h59m33s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 28:C9:7A:FC:58:2B | 2w5d8h3m53s |
| 10.39.0.236 | - | - | 80:BC:37:2C:C7:E0 | 2w3d6h18m14s |
| 10.39.0.7 | - | - | C8:A6:08:04:C5:50 | 2w3d3h23m26s |
| 10.27.60.152 | - | UB-C-WS281 | E4:E7:49:51:F5:BB | 1w1d8h53m26s |
| 10.27.60.154 | - | UB-C-WS281 | E4:E7:49:51:FC:01 | 1w1d8h52m55s |
| 10.27.60.161 | - | UB-C-WS281 | E4:E7:49:51:FB:F9 | 1w1d8h52m37s |
| 10.39.0.64 | lab4-01 | utbk-os | 14:CB:19:0C:14:89 | 1w1d7h26m8s |
| 10.39.0.45 | lab4-02 | utbk-os | 14:CB:19:0C:D7:66 | 1w1d7h25m55s |
| 10.39.0.65 | lab4-07 | utbk-os | 14:CB:19:0C:B2:03 | 1w1d7h24m26s |
| 10.39.0.75 | lab4-05 | utbk-os | 14:CB:19:0C:24:FE | 1w1d7h24m24s |
| 10.39.0.17 | lab4-09 | utbk-os | 14:CB:19:0C:08:4E | 1w1d7h24m16s |
| 10.39.0.11 | lab4-10 | utbk-os | 14:CB:19:0B:DB:0E | 1w1d7h24m16s |
| 10.39.0.66 | lab4-13 | utbk-os | 14:CB:19:0B:DB:23 | 1w1d7h24m11s |
| 10.39.0.67 | lab4-15 | utbk-os | 14:CB:19:0C:48:79 | 1w1d7h24m8s |
| 10.39.0.69 | lab4-16 | utbk-os | 14:CB:19:0C:47:6E | 1w1d7h24m3s |
| 10.39.0.70 | lab4-04 | utbk-os | 14:CB:19:0C:09:ED | 1w1d7h24m3s |
| 10.39.0.55 | lab4-17 | utbk-os | 14:CB:19:0B:37:A3 | 1w1d7h24m2s |
| 10.39.0.46 | lab4-14 | utbk-os | 14:CB:19:0C:14:CD | 1w1d7h24m1s |
| 10.39.0.16 | lab4-12 | utbk-os | 14:CB:19:0C:38:65 | 1w1d7h24m1s |
| 10.39.0.71 | lab4-20 | utbk-os | 14:CB:19:0C:D3:D4 | 1w1d7h23m59s |
| 10.39.0.72 | lab4-21 | utbk-os | 14:CB:19:0C:08:F8 | 1w1d7h23m49s |
| 10.39.0.73 | lab4-11 | utbk-os | 14:CB:19:0C:B6:54 | 1w1d7h23m47s |
| 10.39.0.74 | lab4-pengawas | utbk-os | 14:CB:19:0C:48:D8 | 1w1d7h23m34s |
| 10.39.0.76 | lab4-08 | utbk-os | 14:CB:19:0C:14:8A | 1w1d7h22m31s |
| 10.39.0.77 | lab4-06 | utbk-os | 14:CB:19:0C:18:8A | 1w1d7h18m36s |
| 10.39.0.56 | lab4-18 | utbk-os | 14:CB:19:0C:08:73 | 1w1d7h16m1s |
| 10.39.0.78 | lab4-19 | utbk-os | 14:CB:19:0C:C7:A2 | 1w1d7h14m27s |

**Rekomendasi:** Cek koneksi fisik dan konfigurasi DHCP client. Jika tidak digunakan, disable entri.

---

### 🔴 ANOMALI 2: Perangkat Waiting Tidak Pernah Terlihat > 2 Minggu (HIGH)

Terdapat **29 perangkat waiting** yang `last-seen` sudah lebih dari 2 minggu.

| IP | Comment | Hostname | Last Seen |
|---|---|---|---|
| 10.35.80.83 | BACKUP | 555606b | 449w1d13h7m11s |
| 10.27.60.176 | - | UB-C-WS281 | 31w4d1h58m30s |
| 10.23.80.6 | LAB-UTBK-2 | DESKTOP-C75KJDC | 21w2d3h23m53s |
| 10.23.80.43 | LAB-UTBK-39 | LAB-SIM-01 | 20w1d7h50m28s |
| 10.23.80.44 | LAB-UTBK-40 | LAB-SIM-01 | 20w1d7h50m8s |
| 10.23.80.36 | LAB-UTBK-32 | LAB-SIM-01 | 20w1d7h45m45s |
| 10.23.80.38 | LAB-UTBK-34 | LAB-SIM-01 | 20w1d7h45m39s |
| 10.23.80.40 | LAB-UTBK-36 | LAB-SIM-01 | 20w1d7h45m29s |
| 10.23.80.42 | LAB-UTBK-38 | LAB-SIM-01 | 20w1d7h45m22s |
| 10.23.80.39 | LAB-UTBK-35 | LAB-SIM-01 | 20w1d7h11m19s |
| 10.23.80.34 | LAB-UTBK-30 | LAB-SIM-01 | 20w1d3h19m26s |
| 10.23.80.31 | LAB-UTBK-27 | LAB-SIM-01 | 20w1d3h19m19s |
| 10.23.80.30 | LAB-UTBK-26 | LAB-SIM-01 | 20w1d3h19m18s |
| 10.23.80.28 | LAB-UTBK-24 | LAB-SIM-01 | 20w1d3h19m15s |
| 10.23.80.33 | LAB-UTBK-29 | LAB-SIM-01 | 20w1d3h18m53s |
| 10.23.80.32 | LAB-UTBK-28 | LAB-SIM-01 | 20w1d3h4m28s |
| 10.23.80.35 | LAB-UTBK-31 | LAB-SIM-01 | 20w1d2h32m31s |
| 10.23.80.29 | LAB-UTBK-25 | LAB-SIM-01 | 20w1d2h29m1s |
| 10.23.80.27 | LAB-UTBK-23 | LAB-SIM-01 | 19w4d6h24m12s |
| 10.23.80.25 | LAB-UTBK-21 | LAB-SIM-01 | 19w3d6h34m53s |
| 10.23.80.37 | LAB-UTBK-33 | LAB-SIM-01 | 18w2d4h39m28s |
| 10.23.80.26 | LAB-UTBK-22 | LAB-SIM-01 | 18w2d4h36m8s |
| 10.32.8.100 | - | DESKTOP-14IMVL4 | 12w6d23h19m37s |
| 10.31.16.79 | - | LAB-B24 | 10w2d5h5m24s |
| 10.31.16.80 | - | LAB-B25 | 10w2d5h5m7s |
| 10.31.16.55 | - | LAB-A25 | 10w2d3h46m49s |
| 10.39.0.42 | sw-lab-tik-1-2-barat | H3C-fc582b | 2w5d8h3m53s |
| 10.39.0.236 | - | - | 2w3d6h18m14s |
| 10.39.0.7 | - | - | 2w3d3h23m26s |

**Rekomendasi:** Disable/hapus entri ini untuk bebaskan IP pool.

---

### 🟡 ANOMALI 3: Perangkat Bound Terlalu Lama (> 3 Hari) (MEDIUM)

Terdapat **1 perangkat bound** yang sudah lebih dari 3 hari.

| IP | Comment | Hostname | Age | Expires After |
|---|---|---|---|---|
| 10.27.60.74 | - | pxeutbk | 1w2d6h44m52s | 1w3d13h1m14s |

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

*Report generated: 25 April 2026*
