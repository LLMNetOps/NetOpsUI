# Skenario: Komisioning Router via Containerlab

## Gambaran Umum

Skenario ini mensimulasikan proses komisioning router MikroTik RouterOS dari kondisi fresh menggunakan containerlab sebagai lingkungan lab. Agent platform (llmnetops) mengakses router via SSH dan mengeksekusi konfigurasi awal secara otomatis berdasarkan dokumen spec.

**Tujuan:**
- Validasi workflow komisioning end-to-end menggunakan multi-agent
- Simulasi kondisi nyata: router baru, credential default, belum ada konfigurasi
- Menghasilkan laporan komisioning yang dapat diarsipkan

---

## Komponen Skenario

```
┌─────────────────────────────────────────┐
│  Containerlab (di luar codebase)        │
│                                         │
│  [ROS-LAB-1] ──ether2── [ROS-LAB-2]   │
│   172.20.20.11           172.20.20.12  │
└──────────────┬──────────────────────────┘
               │ SSH via mgmt network
┌──────────────▼──────────────────────────┐
│  llmnetops (codebase ini)               │
│                                         │
│  bambang (supervisor)                   │
│    └─→ joko (config_agent)              │
│          └─→ eko (monitor_agent)        │  [opsional validasi]
│                └─→ document_agent       │
└─────────────────────────────────────────┘
```

---

## Prasyarat

### 1. Software yang Dibutuhkan

| Software | Keterangan |
|----------|------------|
| Docker | Runtime untuk containerlab |
| containerlab | Tool orkestrasi lab jaringan |
| vrnetlab image `vr-routeros` | RouterOS CHR dalam container |
| Python 3.10+ + venv | Untuk llmnetops |
| Ollama | LLM inference lokal |

Install containerlab:
```bash
bash -c "$(curl -sL https://get.containerlab.dev)"
```

### 2. RouterOS CHR Image

Build vrnetlab image RouterOS (butuh file `.chr.vmdk` dari mikrotik.com):

```bash
git clone https://github.com/vrnetlab/vrnetlab.git
cd vrnetlab/routeros
# Letakkan file chr-6.49.10.vmdk di sini
make
```

Image yang dihasilkan: `vrnetlab/vr-routeros:6.49.10`

---

## Langkah 1: Deploy Lab dengan Containerlab

### 1a. Buat file topology

Buat file `lab-netops.clab.yaml` di direktori manapun (di luar codebase):

```yaml
name: netops-lab
prefix: lab

mgmt:
  network: clab-mgmt
  ipv4-subnet: 172.20.20.0/24

topology:
  nodes:
    ROS-LAB-1:
      kind: vr-ros
      image: vrnetlab/vr-routeros:6.49.10
      mgmt-ipv4: 172.20.20.11

    ROS-LAB-2:
      kind: vr-ros
      image: vrnetlab/vr-routeros:6.49.10
      mgmt-ipv4: 172.20.20.12

  links:
    - endpoints: ["ROS-LAB-1:eth1", "ROS-LAB-2:eth1"]
```

### 1b. Deploy

```bash
sudo containerlab deploy -t lab-netops.clab.yaml
```

Output yang diharapkan:
```
+---+------------------+--------------+----------------------------+-------+
| # | Name             | Kind         | Image                      | State |
+---+------------------+--------------+----------------------------+-------+
| 1 | lab-ROS-LAB-1    | vr-ros       | vrnetlab/vr-routeros:6.49  | running |
| 2 | lab-ROS-LAB-2    | vr-ros       | vrnetlab/vr-routeros:6.49  | running |
+---+------------------+--------------+----------------------------+-------+
```

### 1c. Verifikasi akses SSH

```bash
ssh admin@172.20.20.11   # password: kosong, tekan Enter
ssh admin@172.20.20.12
```

Tunggu 30-60 detik setelah deploy sebelum SSH tersedia (RouterOS CHR butuh waktu boot).

---

## Langkah 2: Konfigurasi llmnetops

### 2a. Tambahkan entri lab ke config.yaml

Buka `config.yaml` di root project llmnetops, tambahkan:

```yaml
ssh:
  username: netops       # credential produksi (sudah ada)
  password: "prod123"    # sesuaikan
  networks:
    lab:
      username: admin    # fresh RouterOS CHR default
      password: ""       # password kosong

routers:
  # ... entri router produksi yang sudah ada ...

  # Entri lab (tambahkan di bawah)
  - name: ROS-LAB-1
    host: 172.20.20.11
    role: lab
    network: lab
    ros_version: 7

  - name: ROS-LAB-2
    host: 172.20.20.12
    role: lab
    network: lab
    ros_version: 7
```

### 2b. Verifikasi komisioning spec

File `laporan/commissioning-spec-lab.md` sudah tersedia di codebase.
Buka dan sesuaikan jika ada parameter yang perlu diubah:

| Parameter | Default | Ubah jika |
|-----------|---------|-----------|
| NTP server | `0.id.pool.ntp.org` | Pakai NTP internal |
| SNMP community | `public` | Butuh community berbeda |
| Username baru | `netops` | Butuh nama lain |
| Password | `netops123` | Butuh password berbeda |

---

## Langkah 3: Jalankan llmnetops

```bash
cd /path/to/llmnetops
source .venv/bin/activate
python tui_textual.py
```

---

## Langkah 4: Trigger Komisioning

Di TUI, ketik:

```
komisioning router lab
```

### Alur yang Terjadi

```
bambang (supervisor)
  → mendeteksi kata kunci "komisioning"
  → routing ke joko (config_agent)

joko (config_agent)
  → menemukan skill: commissioning
  → get_report("commissioning-spec-lab")       # baca spec
  → check_reachability(ROS-LAB-1)              # cek koneksi
  → check_reachability(ROS-LAB-2)
  → [APPROVAL] run_command_write(ROS-LAB-1, "/ip address add ...")
  → [APPROVAL] run_command_write(ROS-LAB-1, "/interface bridge add ...")
  → [APPROVAL] run_command_write(ROS-LAB-1, "/user add ...")
  → [APPROVAL] run_command_write(ROS-LAB-1, "/system ntp client set ...")
  → [APPROVAL] run_command_write(ROS-LAB-1, "/snmp set ...")
  → [APPROVAL] run_command_write(ROS-LAB-1, "/ip route add ...")
  → [ulangi untuk ROS-LAB-2]
  → run_command(ROS-LAB-1, "/ip address print")   # validasi
  → run_command(ROS-LAB-1, "/ping 10.10.2.1 count=3")
  → [ulangi validasi untuk ROS-LAB-2]
  → handoff ke document_agent

document_agent
  → buat laporan komisioning
  → simpan ke laporan/commissioning-YYYYMMDD-HHMMSS.md
```

### Approval di TUI

Setiap `run_command_write` memunculkan dialog konfirmasi. Tekan:
- `Y` atau klik "Setuju, jalankan" — eksekusi perintah
- `N` atau `Esc` — tolak (perintah di-skip)

---

## Topologi Target Setelah Komisioning

```
ROS-LAB-1                          ROS-LAB-2
─────────                          ─────────
lo: 10.10.1.1/32                   lo: 10.10.2.1/32
ether2: 10.0.0.1/30 ──────────── ether2: 10.0.0.2/30

Static route:                      Static route:
  10.10.2.1/32 → 10.0.0.2           10.10.1.1/32 → 10.0.0.1

User: netops (group=full)           User: netops (group=full)
NTP:  0.id.pool.ntp.org             NTP:  0.id.pool.ntp.org
SNMP: community=public              SNMP: community=public
```

---

## Validasi Manual (Opsional)

Setelah komisioning selesai, verifikasi dari luar containerlab:

```bash
# SSH pakai credential baru
ssh netops@172.20.20.11

# Di dalam ROS-LAB-1: ping loopback ROS-LAB-2
/ping 10.10.2.1 count=5

# Cek routing table
/ip route print

# Cek NTP sync
/system ntp client print
```

---

## Menghentikan Lab

```bash
sudo containerlab destroy -t lab-netops.clab.yaml
```

Hapus entri lab dari `config.yaml` setelah lab dihentikan.

---

## Troubleshooting

| Masalah | Kemungkinan Penyebab | Solusi |
|---------|---------------------|--------|
| SSH timeout ke router | RouterOS belum selesai boot | Tunggu 60s, coba lagi |
| `admin` ditolak | Password sudah pernah diubah | Destroy + redeploy containerlab |
| Tool result error interface | Nama interface beda di versi CHR | Cek `/interface print` manual, sesuaikan spec |
| Agent stop setelah get_report | LLM baca spec tapi tidak lanjut | Cek `max_iters` config_agent, tambah jika perlu |
| Ping loopback gagal | Static route belum terpasang | Cek `/ip route print` di kedua router |

---

## File Terkait

| File | Keterangan |
|------|------------|
| `laporan/commissioning-spec-lab.md` | Spec yang dibaca agent — parameter & perintah |
| `skills/config/commissioning.md` | Skill yang memandu config_agent |
| `agents/definitions/config_agent.md` | Definisi joko (config_agent) |
| `tools/config_yaml.py` | Tool untuk update config.yaml via agent |

---

## Pengembangan Selanjutnya

- **Scale-up**: Tambah router ke spec (ROS-LAB-3, dst) tanpa ubah skill
- **FRRouting**: Tambah node FRR di containerlab sebagai upstream simulator BGP
- **Hardening**: Tambah skill post-komisioning — nonaktifkan `admin`, set firewall, enable logging
- **OSPF lab**: Tambah konfigurasi OSPF setelah static routing berhasil
