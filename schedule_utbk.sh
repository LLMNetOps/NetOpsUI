#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Jadwal Otomatis Monitoring DHCP Lease — UTBK 2026
#
# Jadwal ujian:
#   Sesi 1 : 05.30 – 10.45
#   Sesi 2 : 12.00 – 16.45
#
# Pengambilan data  : setiap jam mulai 06.00
# Generate laporan  : setelah setiap sesi selesai
# Periode aktif     : 25 April 2026 (2 sesi) dan 26 April 2026 (sesi 1 saja)
#
# Penggunaan:
#   chmod +x schedule_utbk.sh
#   ./schedule_utbk.sh          # daftarkan semua jadwal
#   ./schedule_utbk.sh --list   # tampilkan jadwal yang sudah terdaftar
#   ./schedule_utbk.sh --cancel # batalkan semua jadwal UTBK
# ─────────────────────────────────────────────────────────────

WORKDIR="/home/alan/Documents/03Resource/mikrotik-cek-lease"
PYTHON="python3"
LOG="$WORKDIR/schedule.log"

# ─── Warna output ───
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ─── Cek dependensi ───
if ! command -v at &>/dev/null; then
    echo -e "${RED}ERROR: perintah 'at' tidak ditemukan. Install dengan: sudo apt install at${NC}"
    exit 1
fi

# ─── Mode --list ───
if [[ "$1" == "--list" ]]; then
    echo -e "${YELLOW}Jadwal 'at' yang terdaftar:${NC}"
    atq
    exit 0
fi

# ─── Mode --cancel ───
if [[ "$1" == "--cancel" ]]; then
    echo -e "${YELLOW}Membatalkan semua jadwal 'at'...${NC}"
    # Hapus semua job at milik user ini
    for job in $(atq | awk '{print $1}'); do
        atrm "$job"
        echo "  Dibatalkan job #$job"
    done
    echo -e "${GREEN}Selesai.${NC}"
    exit 0
fi

# ─── Fungsi mendaftarkan satu job ───
schedule_job() {
    local label="$1"
    local datetime="$2"   # format: "HH:MM YYYY-MM-DD"
    local cmd="$3"

    # Cek apakah waktu sudah lewat
    job_epoch=$(date -d "$datetime" +%s 2>/dev/null)
    now_epoch=$(date +%s)
    if [[ $job_epoch -le $now_epoch ]]; then
        echo -e "  ${YELLOW}SKIP${NC} $label ($datetime) — waktu sudah lewat"
        return
    fi

    job_id=$(echo "cd $WORKDIR && $cmd >> $LOG 2>&1" | at "$datetime" 2>&1 | grep -oP 'job \K[0-9]+')
    if [[ -n "$job_id" ]]; then
        echo -e "  ${GREEN}OK${NC}   [$job_id] $label → $datetime"
    else
        echo -e "  ${RED}FAIL${NC} $label → $datetime"
    fi
}

# ─── Fungsi collect data ───
collect() {
    local datetime="$1"
    local label="$2"
    schedule_job "COLLECT $label" "$datetime" "$PYTHON mikrotik_agent.py"
}

# ─── Fungsi generate laporan ───
report() {
    local datetime="$1"
    local label="$2"
    local date_ymd="$3"   # format: YYYYMMDD untuk nama file laporan
    # Hapus laporan hari itu dulu agar data terbaru dimasukkan
    schedule_job "REPORT $label" "$datetime" \
        "rm -f $WORKDIR/laporan/dhcp-lease-${date_ymd}.md && $PYTHON generate_reports.py"
}

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup Jadwal Monitoring DHCP Lease UTBK 2026         ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""

# ═══════════════════════════════════════════════════════
# 25 APRIL 2026 — Sesi 1 & 2
# ═══════════════════════════════════════════════════════
echo -e "${YELLOW}── 25 April 2026 (Sesi 1 & 2) ──${NC}"

# Pengambilan data sesi 1
collect "06:00 2026-04-25" "25 Apr 06:00 (awal sesi 1)"
collect "08:00 2026-04-25" "25 Apr 08:00 (tengah sesi 1)"
collect "10:30 2026-04-25" "25 Apr 10:30 (menjelang akhir sesi 1)"

# Laporan setelah sesi 1 selesai (10:45)
report  "10:55 2026-04-25" "25 Apr 10:55 (laporan sesi 1)" "20260425"

# Pengambilan data sesi 2
collect "12:00 2026-04-25" "25 Apr 12:00 (awal sesi 2)"
collect "14:00 2026-04-25" "25 Apr 14:00 (tengah sesi 2)"
collect "16:30 2026-04-25" "25 Apr 16:30 (menjelang akhir sesi 2)"

# Laporan setelah sesi 2 selesai (16:45)
report  "17:00 2026-04-25" "25 Apr 17:00 (laporan sesi 2)" "20260425"

echo ""

# ═══════════════════════════════════════════════════════
# 26 APRIL 2026 — Sesi 1 saja (berakhir 11:00)
# ═══════════════════════════════════════════════════════
echo -e "${YELLOW}── 26 April 2026 (Sesi 1 saja) ──${NC}"

# Pengambilan data sesi 1
collect "06:00 2026-04-26" "26 Apr 06:00 (awal sesi 1)"
collect "08:00 2026-04-26" "26 Apr 08:00 (tengah sesi 1)"
collect "10:30 2026-04-26" "26 Apr 10:30 (menjelang akhir sesi 1)"

# Laporan final setelah ujian selesai (11:00)
report  "11:10 2026-04-26" "26 Apr 11:10 (laporan final UTBK)" "20260426"

echo ""
echo -e "${GREEN}Selesai! Gunakan './schedule_utbk.sh --list' untuk melihat jadwal.${NC}"
echo -e "Log tersimpan di: ${LOG}"
echo ""
