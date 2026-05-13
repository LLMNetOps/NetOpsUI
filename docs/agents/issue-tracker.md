# Issue Tracker — Local Markdown

Issues disimpan sebagai file Markdown di `.scratch/` di root repo.

## Struktur

```
.scratch/
  <slug-issue>/
    issue.md     # judul, deskripsi, status, label
```

## Workflow

- Buat issue: buat direktori `.scratch/<slug>/issue.md`
- Update status: ubah field `status` di frontmatter
- List issues: `ls .scratch/`

## Format issue.md

```yaml
---
title: "Judul issue"
status: perlu-triage   # lihat triage-labels.md
created: 2026-05-13
---

Deskripsi issue...
```
