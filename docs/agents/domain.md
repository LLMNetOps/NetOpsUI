# Domain Docs

## Layout

Single-context: satu `CONTEXT.md` di root repo + `docs/adr/` untuk architectural decisions.

## Cara Baca

- `CONTEXT.md` — domain language, entitas utama, invariant sistem
- `docs/adr/` — keputusan arsitektur; format: `docs/adr/NNN-judul.md`

## Consumer Rules

- Skills `improve-codebase-architecture`, `diagnose`, `tdd` HARUS baca `CONTEXT.md` sebelum mulai
- Jika ada konflik antara kode dan `CONTEXT.md`, tanya user — jangan asumsikan kode yang benar
- ADR yang ada harus dihormati kecuali user secara eksplisit minta override
