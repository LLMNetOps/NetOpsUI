# LAPORAN STATUS JARINGAN KAMPUS

## Header
- **Tanggal**: {tanggal}
- **Waktu**: {waktu}
- **Author**: Budi (document_agent)
- **Scope**: Seluruh router jaringan kampus

## Ringkasan Eksekutif
{ringkasan}

## 1. REACHABILITY
| Status | Jumlah |
|--------|--------|
| Router UP | {up_count} |
| Router DOWN | {down_count} |

**Router yang Down**: {down_routers}

## 2. RESOURCE UTILIZATION
| Router | CPU | Memory | Status |
|--------|-----|--------|--------|
| {router} | {cpu} | {memory} | {status} |

## 3. STATUS DHCP
**Total Client Aktif**: {total_clients}
**Pool Utilisasi**: {utilisasi}

**Router dengan Masalah DHCP**: {dhcp_issues}

## 4. STATUS SSH ACCESS
| Router | Status | Keterangan |
|--------|--------|------------|
| {router} | {status} | {keterangan} |

## 5. SINKRONISASI WAKTU (NTP)
{ntp_status}

## 6. ANOMALI LOG
{log_anomalies}

## 7. REKOMENDASI
{rekomendasi}

## 8. STATUS KESELURUHAN
**Status**: {overall_status}

---
*Generated: {timestamp}*