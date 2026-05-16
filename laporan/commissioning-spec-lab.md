# Commissioning Spec — Lab RouterOS CHR

**Versi:** 1.0  
**Tanggal:** 2026-05-16  
**Status:** AKTIF — digunakan agent sebagai referensi komisioning  

---

## 1. Topologi

```
[ROS-LAB-1] ──ether2── [ROS-LAB-2]
     |                       |
  loopback               loopback
 10.10.1.1/32          10.10.2.1/32
```

Dua router RouterOS CHR yang dijalankan via containerlab (di luar codebase).
Agent mengakses router via SSH ke IP management yang ditetapkan containerlab.

---

## 2. Inventaris Router

| Nama | Host (mgmt) | Interface Link | Role | Network |
|------|-------------|----------------|------|---------|
| ROS-LAB-1 | 172.20.20.11 | ether2 | lab | lab |
| ROS-LAB-2 | 172.20.20.12 | ether2 | lab | lab |

Credential akses: `admin` / password kosong (default RouterOS CHR fresh).
Credential di config.yaml: gunakan `ssh.networks.lab.username: admin` dan `ssh.networks.lab.password: ""`.

---

## 3. IP Addressing Plan

### 3.1 Link Point-to-Point

| Router | Interface | IP Address | Network |
|--------|-----------|------------|---------|
| ROS-LAB-1 | ether2 | 10.0.0.1/30 | 10.0.0.0/30 |
| ROS-LAB-2 | ether2 | 10.0.0.2/30 | 10.0.0.0/30 |

### 3.2 Loopback (simulasi client)

| Router | Interface | IP Address |
|--------|-----------|------------|
| ROS-LAB-1 | loopback | 10.10.1.1/32 |
| ROS-LAB-2 | loopback | 10.10.2.1/32 |

Interface loopback dibuat via bridge: `/interface bridge add name=loopback`

### 3.3 Static Routing

| Router | Destination | Gateway |
|--------|------------|---------|
| ROS-LAB-1 | 10.10.2.1/32 | 10.0.0.2 |
| ROS-LAB-2 | 10.10.1.1/32 | 10.0.0.1 |

---

## 4. Parameter Konfigurasi

| Parameter | Nilai |
|-----------|-------|
| NTP server | 0.id.pool.ntp.org |
| Timezone | Asia/Jakarta |
| SNMP community | public |
| SNMP contact | netops@lab.local |
| SNMP location | Lab-Containerlab |
| Username baru | netops |
| Password user baru | netops123 |
| Group user | full |

---

## 5. Urutan Konfigurasi per Router

Agent mengeksekusi langkah-langkah berikut untuk **setiap router** secara berurutan:

### Langkah 1 — Interface Link (ether2)

```
/ip address add address=<IP_LINK>/30 interface=ether2
```

Nilai per router:
- ROS-LAB-1: `10.0.0.1/30`
- ROS-LAB-2: `10.0.0.2/30`

### Langkah 2 — Loopback Interface

```
/interface bridge add name=loopback
/ip address add address=<IP_LOOPBACK>/32 interface=loopback
```

Nilai per router:
- ROS-LAB-1: `10.10.1.1/32`
- ROS-LAB-2: `10.10.2.1/32`

### Langkah 3 — Tambah User

```
/user add name=netops password=netops123 group=full
```

Sama untuk semua router.

### Langkah 4 — NTP

```
/system clock set time-zone-name=Asia/Jakarta
/system ntp client set enabled=yes servers=0.id.pool.ntp.org
```

### Langkah 5 — SNMP

```
/snmp set enabled=yes contact=netops@lab.local location=Lab-Containerlab
/snmp community set [ find name=public ] read-access=yes
```

### Langkah 6 — Static Routing

```
/ip route add dst-address=<DST> gateway=<GW>
```

Nilai per router:
- ROS-LAB-1: dst=`10.10.2.1/32` gw=`10.0.0.2`
- ROS-LAB-2: dst=`10.10.1.1/32` gw=`10.0.0.1`

---

## 6. Kriteria Validasi

Setelah semua konfigurasi selesai, agent memvalidasi kondisi berikut:

| # | Cek | Tool | Expected |
|---|-----|------|----------|
| 1 | SSH reachability kedua router | `check_reachability` | ✅ Up |
| 2 | IP address terpasang di ether2 | `run_command` `/ip address print` | 10.0.0.x/30 ada |
| 3 | Loopback terpasang | `run_command` `/ip address print` | 10.10.x.1/32 ada |
| 4 | User netops ada | `run_command` `/user print` | netops terdaftar |
| 5 | NTP enabled | `run_command` `/system ntp client print` | enabled=yes |
| 6 | SNMP enabled | `run_command` `/snmp print` | enabled=yes |
| 7 | Static route aktif | `run_command` `/ip route print` | dst-address ada |
| 8 | Ping loopback peer | `run_command` `/ping 10.10.x.1 count=3` | 3 replies |

---

## 7. Referensi Containerlab

File topology (`lab-netops.clab.yaml`) — disimpan di luar codebase:

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

Deploy: `sudo containerlab deploy -t lab-netops.clab.yaml`  
Destroy: `sudo containerlab destroy -t lab-netops.clab.yaml`

---

## 8. Snippet config.yaml

Tambahkan ke config.yaml codebase:

```yaml
ssh:
  username: netops      # credential produksi/default
  password: "prod123"
  networks:
    lab:
      username: admin   # fresh RouterOS CHR
      password: ""

routers:
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
