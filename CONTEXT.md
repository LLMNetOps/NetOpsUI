# CONTEXT.md — NetOpsUI

Web console untuk operasional jaringan berbasis agent AI. Agent berjalan di backend terpisah; NetOpsUI menyediakan UI dan pengelolaan skill/profil agent.

## Domain Language

| Istilah | Definisi |
|---------|----------|
| Backend | Layanan agent yang dipanggil UI lewat API: **NetOps Agent** (repo saat ini masih bernama palapa-agent) atau **Hermes**. Tepat satu yang aktif. |
| Adapter | Modul di `frontend/js/backends/` yang menerjemahkan API satu backend ke kontrak bersama UI |
| Manager | Service milik NetOpsUI (`server/`, FastAPI + SQLite) untuk skill, profil agent, dan view config yang tidak punya API di backend |
| Thread | Satu percakapan chat. Di NetOps Agent disimpan di browser; di Hermes berupa *session* di server. |
| Run / Giliran | Satu pesan operator beserta seluruh kerja agent sampai jawaban selesai |
| Tool activity | Tool call yang dijalankan agent selama satu giliran (panel kanan AI Chat) |
| Approval | Izin operator sebelum agent menjalankan command berisiko (hanya Hermes: `approval.request`) |
| Skill | Prosedur kerja agent berbentuk `SKILL.md`. Library-nya ada di DB NetOpsUI; *Publish* menyalinnya ke folder skill backend |
| Publish | Menulis `SKILL.md` dari library ke folder skill sebuah backend. Status: Draft / Tersinkron / Perlu publish / Diubah di backend |
| Profil agent | Prompt bernama di DB NetOpsUI. Hermes: dikirim per run sebagai `instructions`. NetOps Agent: diterapkan ke `SOUL.md` |
| SOUL.md | File persona agent (dibaca backend). NetOpsUI hanya menulisnya lewat aksi "Terapkan ke SOUL.md" pada NetOps Agent |
| Belum tersedia | Screen yang datanya belum punya API (`NAV_ITEMS[].unavailable`): Nodes, Reports, Backups, Metrics |

## Invariant Sistem

- UI tidak memuat logika agent/LLM dan tidak pernah memanggil router secara langsung.
- Screen hanya berkomunikasi dengan backend melalui `activeBackend()`; tidak ada `fetch` langsung ke backend dari screen.
- Kredensial (API key Hermes) hanya ada di environment nginx, tidak pernah di browser. Manager tidak pernah mengembalikan nilai `.env`, dan `config.yaml` selalu dimasking.
- Thread milik satu backend; mengganti backend aktif memuat ulang daftar thread dari backend itu.
- Manager hanya menulis ke `skills/` kedua backend dan `SOUL.md` NetOps Agent; sisanya read-only. Publish tidak menimpa file yang bukan hasil publish NetOpsUI tanpa konfirmasi.
- Repo NetOpsUI tidak mengubah repo palapa-agent maupun home backend di luar dua jalur tulis di atas.
