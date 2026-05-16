# CONTEXT.md — llmnetops

Platform operasional jaringan kampus berbasis LangGraph multi-agent.

## Domain Language

| Istilah | Definisi |
|---------|----------|
| Agent | Specialist LLM node di LangGraph graph (monitor, diagnose, config, security, document, netbox) |
| Skill | Prosedur kerja dalam Markdown; dibaca agent saat handle query relevan |
| Tool | Atomic `@tool` function yang SSH ke router MikroTik |
| Supervisor | Orchestrator agent yang route query ke specialist yang tepat |
| Approval | Interrupt mechanism — operator harus confirm sebelum write command dieksekusi |
| Pedoman | `skills/pedoman-agent.md` — global conduct rules untuk semua agent, hot-reload |
| Commissioning | Workflow konfigurasi router baru dari fresh via skill + design doc |

## Entitas Utama

- **Router** — MikroTik RouterOS v6/v7, diakses via SSH dari `config.yaml`
- **Operator** — manusia yang approve/tolak write commands di TUI
- **Agent Log** — append-only list events yang dikonsumsi TUI (`agent_log` di state)
- **TUI** — `tui_textual.py` (Textual framework, aktif); `tui.py` (ncurses, legacy)

## Invariant Sistem

- Agent tidak boleh eksekusi write command tanpa approval operator
- `tui.py` tidak boleh punya LLM logic — hanya consume `agent.py` public API
- Safety net AIMessage dan loop guard di `agents/nodes.py` tidak boleh dihapus
- `TOOL_MAP` di `agents/tools.py` adalah source of truth untuk tool availability per agent
- Backup wajib sebelum write pertama ke setiap router (enforced di `config_node`, bukan LLM)
- Global conduct rules dikelola di `skills/pedoman-agent.md` — jangan hardcode di nodes.py
