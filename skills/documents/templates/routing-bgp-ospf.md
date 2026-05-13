# LAPORAN STATUS ROUTING — {router_name}
**Tanggal**: {tanggal dari get_current_time}
**Waktu**: {waktu WIB dari get_current_time}
**Author**: Budi (document_agent)
**Router**: {router_name} — {host dari get_system_info}
**Platform**: MikroTik {board-name dari get_system_info}, RouterOS {version dari get_system_info}
**Local AS**: {local_as dari baris pertama get_bgp_sessions} ({identitas organisasi jika diketahui})

---

## RINGKASAN EKSEKUTIF

{2-3 kalimat: sebutkan peran router (gateway/Route Reflector/dll), jumlah BGP session, jumlah OSPF neighbor, dan anomali utama}

| Komponen | Status | Detail |
|----------|--------|--------|
| Sistem | {✅/⚠/❌} | Uptime {uptime}, CPU {cpu-load}%, RAM {free-memory}/{total-memory} |
| BGP | {✅/⚠/❌} | {established}/{total} session established, {anomali jika ada} |
| OSPF | {✅/⚠/❌} | {full}/{total} neighbor Full, {anomali jika ada} |

---

## 1. SISTEM

{Salin dari output get_system_info — nilai PERSIS, bukan estimasi}

| Parameter | Nilai |
|-----------|-------|
| Platform | {board-name} |
| RouterOS | {version} ({bulan dan tahun rilis jika diketahui}) |
| Uptime | {uptime} (sejak ~{hitung mundur dari tanggal sekarang}) |
| CPU | {cpu-load}% ({cpu-count} core {architecture-name}) |
| Memory | {free-memory} bebas / {total-memory} total |
| Storage | {free-hdd-space} bebas / {total-hdd-space} total |

{Jika versi RouterOS > 12 bulan dari tanggal laporan, tambahkan catatan:
"RouterOS {version} sudah {N} bulan. Pertimbangkan upgrade ke versi terkini untuk perbaikan stabilitas BGP/OSPF."}

---

## 2. BGP — {N_established}/{N_total} Session Established

{Sumber: output get_bgp_sessions — salin nilai PERSIS dari tabel tool, jangan estimasi}
{Hitung sendiri jumlah eBGP vs iBGP dari kolom Type di output tool}

### 2a. eBGP — Upstream & Peers

{Semua baris dengan Type=eBGP dari output get_bgp_sessions}

| # | Name (dari kolom Name) | RemAS | RemoteIP | Uptime | Pfx | Status |
|---|----------------------|-------|----------|--------|-----|--------|
{salin baris eBGP satu per satu dari output tool — jumlah baris harus sama persis}

### 2b. iBGP — {Route Reflector / Client}

{Semua baris dengan Type=iBGP dari output get_bgp_sessions}
{Jika ada local.role=ibgp-rr di data → router ini adalah Route Reflector}

| # | Name (dari kolom Name) | RemAS | RemoteIP | Uptime | Pfx | Status |
|---|----------------------|-------|----------|--------|-----|--------|
{salin baris iBGP satu per satu dari output tool — jumlah baris harus sama persis}

### 2c. Analisis BGP

**Session DOWN** ({daftar dari baris ✗DWN di output tool}):
{untuk tiap session DOWN: tulis nama lengkap, AS, IP, dan last-stopped dari bagian "⚠ session DOWN" di output tool}

**Session uptime pendek < 24 jam** (baru reconnect, anomali):
{HANYA session dengan uptime < 24h — session dengan 1d, 2d, 5w bukan "uptime pendek"}
{Jika tidak ada: "Tidak ada session dengan uptime < 24 jam"}

**Pola primary/backup** (jika ada dua session ke institusi yang sama):
{analisis mana yang aktif, mana yang down, apakah intended failover}
{sebutkan last-stopped dari session DOWN untuk konteks "sudah berapa lama down"}

**Total prefix diterima** (pisahkan IPv4 dan IPv6):
- IPv4: {jumlahkan Pfx dari sesi dengan RemoteIP = x.x.x.x (tanpa colon)}
- IPv6: {jumlahkan Pfx dari sesi dengan RemoteIP = 2001:.../2407:.../dll (mengandung colon)}
{Jangan campur sesi IPv4 dan IPv6 — RemoteIP dengan colon adalah sesi IPv6}

---

## 3. OSPF — {N_full}/{N_total} Neighbor Full

{Sumber: output get_ospf_neighbors — salin SEMUA baris, jumlah harus sama persis}
Instance: {ospf_instance dari output}, Area: {ospf_area dari output}

| # | Address | Router ID | State | SC | Adjacency | Area |
|---|---------|-----------|-------|----|-----------|------|
{salin SEMUA baris dari output get_ospf_neighbors — tidak boleh kurang atau lebih}
{kolom SC = state-changes dari output tool}

{Untuk tiap baris dengan State != Full, tambahkan sub-bagian:}

### 3a. Anomali: {Address} — State {State}

- **Router ID**: {router_id}
- **State-changes**: {nilai dari kolom SC} → {interpretasi: "=1 berarti belum pernah established" / "=N berarti pernah naik N kali, sekarang jatuh lagi"}
- **Identifikasi peer**: {cek apakah Address atau RouterID cocok dengan RemoteIP di get_bgp_sessions → lihat kolom Name untuk nama institusi}
- **Cross-reference BGP**: {cek apakah Address atau RouterID muncul di output get_bgp_sessions}
  - Jika ditemukan: "BGP ke peer ini {established/down} ({nama session}), artinya {L3 OK atau tidak}"
  - Jika tidak ditemukan: "Tidak ada BGP session ke peer ini — kemungkinan masalah L3"
- **Kemungkinan penyebab**: {berdasarkan evidence yang ada, bukan dugaan umum}
  - L3 OK (BGP established): firewall DROP protocol 89, Hello/dead interval mismatch, authentication mismatch, area ID berbeda
  - L3 tidak jelas: kemungkinan masalah link fisik atau routing ke subnet ini

{Untuk tiap baris dengan State=Full tapi SC > 20 — tool sudah memflag ini:}

### 3b. Perhatian: {Address} — State-Changes Tinggi ({nilai SC}x)

- **State sekarang**: Full, adjacency {adjacency uptime}
- **State-changes**: {nilai} → {interpretasi: "router baru reconnect {adjacency uptime} tapi sebelumnya mengalami {nilai} kali flapping"}
- **Konteks**: adjacency stabil sekarang tapi riwayat instabilitas perlu dipantau
- **Tindakan**: monitor selama {N} hari ke depan; jika flapping terulang, investigasi link fisik

---

## 4. LOG

{Dari output get_router_log topic=bgp dan topic=ospf}

**BGP log**: {event yang ditemukan: hold timer, connection closed, authentication, dll}
{Jika kosong: "Tidak ada event BGP dalam window log"}

**OSPF log**: {event yang ditemukan: neighbor state change, authentication failure, dll}
{Jika kosong: "Tidak ada event OSPF dalam window log" — ini bisa berarti masalah OSPF sudah lama (lebih dari window log)}

**Monitoring script**: {cek get_router_log(topic="script") — jika ada entri seperti "Host x.x.x.x is up", sebutkan IP yang dipantau}
{Jika kosong: "Tidak ada script monitoring di log"}

---

## 5. REKOMENDASI

{Urutkan dari dampak tertinggi, sertakan perintah RouterOS yang bisa langsung dieksekusi}

### Prioritas 1 — {judul}
{detail + perintah konkret}

### Prioritas 2 — {judul}
{detail + perintah konkret}

### Prioritas 3 — {judul jika ada}
{detail}

{Jika RouterOS sudah > 12 bulan: tambahkan prioritas untuk upgrade RouterOS}

---

## 6. STATUS AKHIR

| Kategori | Status |
|----------|--------|
| Sistem | {✅ SEHAT / ⚠ PERHATIAN / ❌ KRITIS} |
| BGP | {✅ / ⚠ / ❌} dengan detail |
| OSPF | {✅ / ⚠ / ❌} dengan detail |
| Konektivitas aktif | {✅ NORMAL / ⚠ DEGRADED / ❌ DOWN} |

**Kesimpulan**: {satu kalimat verdict — sebutkan status operasional DAN apakah anomali yang ada mempengaruhi layanan aktif atau tidak}
