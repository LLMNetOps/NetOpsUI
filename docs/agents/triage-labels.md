# Triage Labels

Lima status canonical dalam Bahasa Indonesia.

| Role | Label | Keterangan |
|------|-------|------------|
| needs-triage | `perlu-triage` | Maintainer perlu evaluasi |
| needs-info | `perlu-info` | Menunggu info dari reporter |
| ready-for-agent | `siap-agent` | Fully specified, siap diambil AFK agent |
| ready-for-human | `siap-manusia` | Butuh implementasi manusia |
| wontfix | `tidak-dikerjakan` | Tidak akan dikerjakan |

## State Machine

```
perlu-triage → perlu-info | siap-agent | siap-manusia | tidak-dikerjakan
perlu-info   → perlu-triage | tidak-dikerjakan
siap-agent   → siap-manusia  (jika perlu human review setelah agent selesai)
```
