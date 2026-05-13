# Pola Komunikasi Antar Agent di LangGraph

**Konteks:** Dokumen lanjutan dari [LANGGRAPH_FUNDAMENTALS.md](./LANGGRAPH_FUNDAMENTALS.md).  
Membahas bagaimana agent berkomunikasi satu sama lain, mekanisme yang tersedia di LangGraph,
dan pola yang relevan untuk project `llmnetops`.

**Status per kode:**
- ✅ Sudah diimplementasikan di project ini
- 🔧 Implementasi yang diusulkan (belum ada di kode)
- 💡 Konsep untuk eksplorasi lebih lanjut

---

## Daftar Isi

1. [Mengapa Komunikasi Antar Agent Penting](#1-mengapa-komunikasi-antar-agent-penting)
2. [Arsitektur Saat Ini: Hub-and-Spoke](#2-arsitektur-saat-ini-hub-and-spoke)
3. [Empat Mekanisme Komunikasi LangGraph](#3-empat-mekanisme-komunikasi-langgraph)
4. [Pola untuk Project Ini](#4-pola-untuk-project-ini)
5. [Studi Kasus: Audit Komprehensif](#5-studi-kasus-audit-komprehensif)
6. [Perbandingan Semua Pola](#6-perbandingan-semua-pola)
7. [Referensi Kode](#7-referensi-kode)

---

## 1. Mengapa Komunikasi Antar Agent Penting

### Masalah dengan Komunikasi Implisit

Saat ini, agent berkomunikasi secara **implisit** — eko menulis narasi teks ke `messages`, agus membaca teks itu dan harus "memahami" apa yang dimaksud eko.

```
eko menulis ke messages:
  "Hasil monitoring: Router DTI tidak dapat dijangkau (timeout setelah 3x ping).
   Router FIB-GW CPU mencapai 87%, memory 72%. DHCP pool Rektorat utilisasi 91%."

agus membaca messages dan harus parse:
  - DTI unreachable? → ya, ada di teks
  - Router mana yang perlu didiagnosa? → harus extract dari narasi
  - Prioritas diagnosa? → harus inferensi dari konteks
```

**Masalahnya:**
- Informasi yang relevan tersembunyi dalam narasi panjang
- Agent penerima harus kerja ekstra untuk mengekstrak data
- Tidak ada kontrak/struktur yang jelas antar agent
- Mudah terjadi salah interpretasi

### Komunikasi Eksplisit yang Ideal

```
eko menulis ke state (terstruktur):
  agent_handoff = {
      "from": "monitor_agent",
      "anomalies": [
          {"router": "DTI", "issue": "unreachable", "severity": "critical"},
          {"router": "FIB-GW", "issue": "cpu_high", "value": 87, "severity": "warning"},
      ],
      "focus_routers": ["DTI", "FIB-GW"],
      "skip_routers": ["REKTORAT", "FIB-LAB"]
  }

agus membaca langsung:
  focus = state["agent_handoff"]["focus_routers"]  # ["DTI", "FIB-GW"]
  # → langsung tahu harus diagnosa DTI dan FIB-GW, tidak perlu parse teks
```

---

## 2. Arsitektur Saat Ini: Hub-and-Spoke ✅

### Cara Kerjanya

Semua komunikasi antar agent **selalu melewati bambang** (supervisor). Bambang adalah pusat (hub), specialist adalah jari-jari (spoke).

```
                    bambang
                   /  |  |  \
                  /   |  |   \
               eko  agus joko satria budi
```

**Flow untuk query sederhana (satu agent):**
```
User → bambang (LLM #1) → eko → bambang (LLM #2) → END
```

**Flow untuk query kompleks (semua agent):**
```
User
 └─► bambang (LLM #1) → eko
                          └─► bambang (LLM #2) → agus
                                                    └─► bambang (LLM #3) → joko
                                                                              └─► bambang (LLM #4) → satria
                                                                                                        └─► bambang (LLM #5) → budi
                                                                                                                                  └─► bambang (LLM #6) → END
```

### Kode yang Mengimplementasikan Ini

```python
# agents/graph.py — semua specialist kembali ke supervisor (unconditional)
for agent in ("monitor_agent", "diagnose_agent", "config_agent",
              "security_agent", "document_agent"):
    builder.add_edge(agent, "supervisor")
```

```python
# agents/nodes.py — setiap specialist selalu set next_agent = "supervisor"
return {
    "messages": [final_msg],
    "active_agent": agent_name,
    "next_agent": "supervisor",   # ← selalu kembali ke bambang
    "agent_log": logs,
}
```

### Kelebihan

- Bambang punya **visibilitas penuh** — selalu tahu apa yang terjadi
- Bisa **override** keputusan kapanpun (routing dinamis berdasarkan hasil)
- Sederhana untuk dipahami dan di-debug

### Keterbatasan

- **N+1 LLM calls** — setiap langkah butuh bambang memanggil LLM lagi
- **Tidak ada struktur data** antar agent — hanya teks di `messages`
- **Tidak ada paralelisme** — eko dan satria tidak bisa jalan bersamaan
- **Latency tinggi** untuk query yang melibatkan banyak agent

---

## 3. Empat Mekanisme Komunikasi LangGraph

### Mekanisme 1: Shared State ✅

Cara paling dasar. Agent baca/tulis ke field state yang sama. Sudah digunakan sepenuhnya di project ini.

```python
# Agent A menulis ke state
def monitor_node(state):
    return {
        "messages": [AIMessage("DTI unreachable, FIB-GW CPU 87%")],
        "active_agent": "monitor_agent",
    }

# Agent B membaca dari state (messages yang sama)
def diagnose_node(state):
    # messages[-10:] sudah include hasil monitor_node
    context = state["messages"][-10:]
    # ... agus membaca konteks eko dari messages
```

**Karakteristik:**
- Komunikasi **implisit** — lewat akumulasi messages
- Tidak ada struktur khusus — hanya teks
- Cocok untuk: konteks percakapan umum, riwayat interaksi

---

### Mekanisme 2: Command Object 🔧

Node bisa return `Command` — sebuah objek khusus yang sekaligus **mengupdate state DAN menentukan routing** secara eksplisit.

```python
from langgraph.types import Command

# TANPA Command (cara sekarang)
def monitor_node(state):
    return {
        "messages": [final_msg],
        "next_agent": "supervisor",   # harus lewat bambang dulu
    }

# DENGAN Command (routing langsung)
def monitor_node(state):
    anomalies = [...hasil analisis...]

    return Command(
        goto="diagnose_agent",        # langsung ke agus, skip bambang
        update={
            "messages": [final_msg],
            "active_agent": "monitor_agent",
            "agent_handoff": {         # data terstruktur untuk agus
                "from": "monitor_agent",
                "anomalies": anomalies,
                "focus_routers": [a["router"] for a in anomalies if a["severity"] == "critical"],
            },
        }
    )
```

**Yang perlu ditambahkan ke state jika menggunakan ini:**

```python
# agent.py — tambah field agent_handoff
class NetworkOpsState(TypedDict):
    messages:       Annotated[list, add_messages]
    next_agent:     str
    active_agent:   str
    injected_skills: list[str]
    agent_log:      Annotated[list[AgentLogEntry], _append]
    pending_approval: ApprovalRequest | None
    approval_decision: str | None
    # BARU:
    agent_handoff:  dict | None    # data terstruktur dari agent sebelumnya
```

**Yang perlu diubah di graph:**

```python
# agents/graph.py — tambah conditional edge dari monitor_agent
# (bukan lagi unconditional ke supervisor)
builder.add_conditional_edges(
    "monitor_agent",
    lambda state: state.get("next_agent", "supervisor"),
    {
        "diagnose_agent": "diagnose_agent",
        "supervisor":     "supervisor",
    }
)
```

**Karakteristik:**
- Komunikasi **eksplisit** — data terstruktur lewat `agent_handoff`
- Agent bisa langsung handoff ke agent lain **tanpa bambang**
- Bambang tidak tahu handoff terjadi (kehilangan visibilitas)
- Cocok untuk: chaining yang sudah jelas urutannya (eko selalu ke agus jika ada anomali)

---

### Mekanisme 3: Send API (Paralel) 💡

`Send` memungkinkan satu node **menjalankan beberapa node secara bersamaan** (fan-out), kemudian mengumpulkan hasilnya (fan-in).

```python
from langgraph.types import Send

# bambang bisa jalankan eko DAN satria secara paralel
def supervisor_node(state):
    query = state["messages"][-1].content

    # Jika butuh audit komprehensif → fan-out ke monitor + security sekaligus
    if is_comprehensive_audit(query):
        return [
            Send("monitor_agent",  {**state, "focus": "health_check"}),
            Send("security_agent", {**state, "focus": "security_audit"}),
        ]

    # Jika query biasa → routing normal
    return {"next_agent": decide_single_agent(query)}
```

**Visualisasi fan-out + fan-in:**

```
bambang
  ├──Send──► eko    (jalan paralel)
  └──Send──► satria (jalan paralel)
               │
               ▼ (keduanya selesai, hasil di-merge ke state)
             budi (kompilasi laporan dari hasil eko + satria)
```

**Catatan penting untuk Send API:**

```python
# State harus punya reducer yang aman untuk parallel writes
# Tanpa reducer yang tepat → data dari eko dan satria bisa saling timpa!

class NetworkOpsState(TypedDict):
    # ✅ Aman untuk parallel — add_messages merge dengan benar
    messages: Annotated[list, add_messages]

    # ✅ Aman untuk parallel — _append merge dengan benar
    agent_log: Annotated[list[AgentLogEntry], _append]

    # ❌ TIDAK aman untuk parallel — field str akan ditimpa
    # Jika eko dan satria keduanya menulis next_agent, hanya satu yang tersimpan
    next_agent: str
```

**Karakteristik:**
- Paling **efisien secara waktu** — agent jalan bersamaan
- Cocok untuk: agent yang independen satu sama lain (tidak saling bergantung)
- Butuh perancangan state yang hati-hati (reducer harus benar)
- Tidak cocok jika: agus butuh hasil eko sebelum bisa mulai

---

### Mekanisme 4: Subgraph 💡

Sekelompok node yang membentuk **graph tersendiri** dan dipanggil sebagai satu node tunggal oleh graph utama.

```python
# Buat sub-graph untuk workflow audit
def build_audit_subgraph():
    builder = StateGraph(NetworkOpsState)
    builder.add_node("monitor_agent",  monitor_node)
    builder.add_node("diagnose_agent", diagnose_node)
    builder.add_edge(START, "monitor_agent")
    builder.add_edge("monitor_agent", "diagnose_agent")
    builder.add_edge("diagnose_agent", END)
    return builder.compile()

audit_subgraph = build_audit_subgraph()

# Graph utama: bambang memanggil subgraph sebagai satu node
def build_main_graph():
    builder = StateGraph(NetworkOpsState)
    builder.add_node("supervisor",     supervisor_node)
    builder.add_node("audit_workflow", audit_subgraph)   # ← subgraph sebagai node
    builder.add_node("document_agent", document_node)
    ...
```

**Flow:**
```
bambang → [audit_workflow] → budi → END
              ↕ (internal subgraph)
           eko → agus → joko
```

Dari sudut pandang bambang, `audit_workflow` terlihat seperti node biasa.

**Karakteristik:**
- **Reusable** — subgraph bisa dipakai di beberapa graph utama
- **Encapsulated** — detail internal tersembunyi dari graph utama
- Cocok untuk: workflow yang sering dijalankan sebagai satu unit
- Lebih kompleks untuk di-debug (dua level graph)

---

## 4. Pola untuk Project Ini

### Pola A: Workflow Queue 🔧

Bambang merencanakan **urutan agent** sejak awal untuk query kompleks. Specialist berjalan berantai tanpa memanggil LLM bambang di setiap langkah.

**Perubahan state yang dibutuhkan:**

```python
# agent.py
class NetworkOpsState(TypedDict):
    messages:         Annotated[list, add_messages]
    next_agent:       str
    active_agent:     str
    injected_skills:  list[str]
    agent_log:        Annotated[list[AgentLogEntry], _append]
    pending_approval: ApprovalRequest | None
    approval_decision: str | None
    workflow_queue:   list[str]    # ← BARU: sisa agent yang perlu dijalankan
```

**Perubahan supervisor:**

```python
# agents/nodes.py — supervisor_node
# Bambang return workflow jika query kompleks
def supervisor_node(state):
    ...
    data = json.loads(llm_response)

    workflow = data.get("workflow", [])      # list agent dari LLM

    if len(workflow) > 1:
        # Mode workflow: jalankan berantai tanpa bambang di tengah
        return {
            "next_agent":     workflow[0],   # mulai dari agent pertama
            "workflow_queue": workflow[1:],  # sisa antrian
            ...
        }
    else:
        # Mode normal: routing biasa
        return {
            "next_agent":     data.get("next_agent", "monitor_agent"),
            "workflow_queue": [],
            ...
        }
```

**Supervisor prompt yang diperbarui:**

```
Balas HANYA dengan JSON valid.
Untuk query SEDERHANA (satu domain):
{"next_agent": "monitor_agent", "workflow": [], "relevant_skills": [], "reasoning": "..."}

Untuk query KOMPLEKS (butuh banyak agent):
{"next_agent": "monitor_agent", "workflow": ["monitor_agent", "diagnose_agent", "document_agent"],
 "relevant_skills": [], "reasoning": "audit komprehensif butuh monitoring + diagnosa + laporan"}

Field next_agent harus salah satu: monitor_agent, diagnose_agent, config_agent, security_agent, document_agent, END
```

**Perubahan specialist node factory:**

```python
# agents/nodes.py — _make_specialist_node
def _node(state: "NetworkOpsState") -> dict:
    ...
    # Cek apakah ada workflow queue
    queue = list(state.get("workflow_queue") or [])

    if queue:
        next_agent = queue.pop(0)    # ambil agent berikutnya
        log_msg = f"← handoff ke {AGENT_ALIAS.get(next_agent, next_agent)} (workflow)"
    else:
        next_agent = "supervisor"    # kembali ke bambang seperti biasa
        log_msg = "← kembali ke supervisor"

    logs.append(_log(agent_name, "routing", log_msg))

    return {
        "messages":       [final_msg],
        "active_agent":   agent_name,
        "next_agent":     next_agent,
        "workflow_queue": queue,      # sisa antrian yang diperbarui
        "agent_log":      logs,
    }
```

**Perubahan graph — conditional edges dari specialist:**

```python
# agents/graph.py
def route_after_specialist(state: dict) -> str:
    return state.get("next_agent", "supervisor")

# Ganti unconditional edge dengan conditional
for agent in ("monitor_agent", "diagnose_agent", "config_agent",
              "security_agent", "document_agent"):
    builder.add_conditional_edges(
        agent,
        route_after_specialist,
        {
            "monitor_agent":  "monitor_agent",
            "diagnose_agent": "diagnose_agent",
            "config_agent":   "config_agent",
            "security_agent": "security_agent",
            "document_agent": "document_agent",
            "supervisor":     "supervisor",
        }
    )
```

**Visualisasi flow dengan Workflow Queue:**

```
# Query: "audit komprehensif + simpan laporan"

bambang (LLM #1)
  workflow = ["monitor_agent", "diagnose_agent", "config_agent", "security_agent", "document_agent"]
  next_agent = "monitor_agent"
  workflow_queue = ["diagnose_agent", "config_agent", "security_agent", "document_agent"]
        │
        ▼
eko (monitor_agent)
  workflow_queue = ["diagnose_agent", "config_agent", "security_agent", "document_agent"]
  → selesai → next_agent = "diagnose_agent"
  workflow_queue = ["config_agent", "security_agent", "document_agent"]
        │ (langsung, tanpa bambang)
        ▼
agus (diagnose_agent)
  → selesai → next_agent = "config_agent"
  workflow_queue = ["security_agent", "document_agent"]
        │
        ▼
joko (config_agent)
  → selesai → next_agent = "security_agent"
  workflow_queue = ["document_agent"]
        │
        ▼
satria (security_agent)
  → selesai → next_agent = "document_agent"
  workflow_queue = []
        │
        ▼
budi (document_agent)
  → selesai → workflow_queue kosong → next_agent = "supervisor"
        │
        ▼
bambang (LLM #2) → END

Total bambang LLM calls: 2 (vs 6 sebelumnya)
```

---

### Pola B: Typed Handoff (Command + agent_handoff) 🔧

Menggabungkan Workflow Queue dengan **data terstruktur** antar agent. Setiap agent yang handoff ke agent berikutnya menyertakan ringkasan temuan dalam format yang sudah diketahui penerimanya.

```python
# Definisi struktur handoff per agent
class MonitorHandoff(TypedDict):
    critical_routers: list[str]     # router yang butuh diagnosa segera
    warning_routers:  list[str]     # router dengan kondisi mengkhawatirkan
    dhcp_issues:      list[dict]    # pool yang bermasalah
    anomaly_summary:  str           # ringkasan singkat untuk LLM

class DiagnoseHandoff(TypedDict):
    root_causes:      list[dict]    # {"router": str, "issue": str, "evidence": str}
    config_to_check:  list[str]     # router yang perlu dicek konfigurasinya
    security_flags:   list[str]     # hal yang perlu diaudit keamanannya
```

```python
# monitor_node — menulis handoff terstruktur
def _node(state):
    # ... jalankan monitoring ...

    # Buat handoff untuk agus
    handoff: MonitorHandoff = {
        "critical_routers": [r for r in results if r["status"] == "unreachable"],
        "warning_routers":  [r for r in results if r["cpu"] > 80],
        "dhcp_issues":      [p for p in dhcp_results if p["utilization"] > 85],
        "anomaly_summary":  f"{len(critical)} router kritis, {len(warning)} perlu perhatian",
    }

    return Command(
        goto="diagnose_agent",
        update={
            "messages":      [final_msg],
            "active_agent":  "monitor_agent",
            "agent_handoff": handoff,    # ← terstruktur, bukan teks
            "agent_log":     logs,
        }
    )

# diagnose_node — membaca handoff terstruktur
def _node(state):
    # Baca handoff dari eko — tidak perlu parse teks
    handoff = state.get("agent_handoff") or {}
    focus_routers = handoff.get("critical_routers", [])

    # Langsung diagnosa router yang spesifik
    sys_content = f"""
    {_SPECIALIST_SYS}
    PRIORITAS: Diagnosa router berikut terlebih dahulu: {focus_routers}
    Konteks dari monitoring: {handoff.get("anomaly_summary", "")}
    """
```

---

### Pola C: Paralel Fan-out untuk Audit Independen 💡

Cocok ketika dua agent bisa jalan bersamaan karena tugasnya **tidak saling bergantung**.

```
# eko dan satria independen — tidak butuh hasil satu sama lain
# bisa jalan paralel, budi tunggu keduanya

bambang
  ├──Send──► eko    ──┐
  └──Send──► satria ──┤
                      ▼ (keduanya selesai)
                    budi (kompilasi hasil eko + satria)
```

```python
# agents/nodes.py — supervisor dengan fan-out logic
def supervisor_node(state):
    query = state["messages"][-1].content if state["messages"] else ""

    # Deteksi kebutuhan audit paralel
    needs_parallel = any(kw in query.lower() for kw in
                         ["audit komprehensif", "laporan lengkap", "semua domain"])

    if needs_parallel:
        return [
            Send("monitor_agent",  state),
            Send("security_agent", state),
        ]

    # Routing normal
    ...
```

```python
# agents/graph.py — tambah fan-in node (budi sebagai aggregator)
# Setelah eko DAN satria selesai, jalankan budi
builder.add_node("budi_aggregator", budi_aggregator_node)
builder.add_edge("monitor_agent",  "budi_aggregator")
builder.add_edge("security_agent", "budi_aggregator")
```

**Catatan penting:** Untuk pola ini, semua field yang ditulis paralel **harus punya reducer `append`**. Field tanpa reducer akan race condition.

---

## 5. Studi Kasus: Audit Komprehensif Jaringan Kampus

### Skenario

**Operator mengetik:**
> *"Lakukan audit menyeluruh kondisi jaringan kampus — cek kesehatan, diagnosa masalah, verifikasi konfigurasi, audit keamanan, dan simpan hasilnya sebagai laporan lengkap."*

### Apa yang Terjadi di Setiap Agent

```
bambang (supervisor)
  Input : query operator
  Proses: analisis query → butuh semua domain → set workflow queue
  Output: workflow = [monitor_agent, diagnose_agent, config_agent, security_agent, document_agent]

eko (monitor_agent)
  Input : query + workflow_queue penuh
  Proses:
    • check_reachability semua router
    • get_system_info (CPU, RAM, uptime) per router
    • get_traffic_summary
    • audit_dhcp
    • get_router_log
  Output (temuan):
    • DTI: UNREACHABLE
    • FIB-GW: CPU 87%, kemungkinan routing loop
    • REKTORAT: DHCP pool 91% penuh
  next_agent: diagnose_agent (dari workflow queue)

agus (diagnose_agent)
  Input : messages include hasil eko
  Proses:
    • run_diagnostic("DTI") → interface ether1 flap
    • run_diagnostic("FIB-GW") → routing loop konfirmasi
    • get_router_log("DTI") → "ether1 link down" 3x dalam 1 jam
    • search_device untuk client yang terdampak DTI
  Output (temuan):
    • DTI: ether1 flap — kemungkinan kabel fisik atau SFP rusak
    • FIB-GW: static route 0.0.0.0/0 conflict dengan OSPF default route
    • 47 client tidak dapat IP karena DTI down
  next_agent: config_agent (dari workflow queue)

joko (config_agent)
  Input : messages include hasil eko + agus
  Proses:
    • get_router_config("FIB-GW") → cek routing table
    • run_command("FIB-GW", "/ip route print") → konfirmasi conflict
    • get_router_config("DTI") → cek interface config
  Output (temuan):
    • FIB-GW: static default route distance=1, OSPF default distance=110 → conflict
    • DTI: interface ether1 tidak ada cable-test history
    • Backup config terakhir: 14 hari lalu
  next_agent: security_agent (dari workflow queue)

satria (security_agent)
  Input : messages include hasil eko + agus + joko
  Proses:
    • audit_security semua router
    • get_router_log filter "login"
    • run_command semua router cek user list
  Output (temuan):
    • 3 router masih pakai password default admin/admin
    • FIB-GW: SSH port 22 accessible dari IP publik
    • 2 router NTP tidak sinkron (selisih >5 menit)
    • Login attempt gagal dari 103.45.xx.xx (bukan IP kampus)
  next_agent: document_agent (dari workflow queue)

budi (document_agent)
  Input : semua messages dari eko, agus, joko, satria
  Proses:
    • list_templates() → pilih security-assessment.md
    • read_template("security-assessment.md") → load struktur
    • Kompilasi semua temuan dari messages
    • Buat dokumen lengkap sesuai template
    • write_document("network-audit_20260501_143022.md", content)
  Output:
    • File tersimpan di laporan/network-audit_20260501_143022.md
    • Notifikasi ke operator
  next_agent: supervisor (workflow_queue kosong)

bambang (supervisor)
  Input : messages include respons budi
  Proses: budi sudah reply → END
  Output: → END
```

### Perbandingan Flow: Sekarang vs dengan Workflow Queue

```
SEKARANG (hub-and-spoke):
  bambang(LLM) → eko → bambang(LLM) → agus → bambang(LLM) → joko
  → bambang(LLM) → satria → bambang(LLM) → budi → bambang(LLM) → END
  
  Total: 6x LLM call bambang
  Estimasi waktu tambahan: +30-60 detik (tergantung model)

DENGAN WORKFLOW QUEUE:
  bambang(LLM) → eko → agus → joko → satria → budi → bambang(LLM) → END

  Total: 2x LLM call bambang
  Estimasi penghematan: 4x LLM call (~20-40 detik lebih cepat)
```

### Data yang Mengalir Antar Agent

```
State setelah semua agent selesai:

messages = [
  HumanMessage("Lakukan audit menyeluruh..."),
  AIMessage("Hasil monitoring: DTI unreachable..."),        ← dari eko
  AIMessage("Diagnosa: interface flap, routing loop..."),   ← dari agus
  AIMessage("Config: static route conflict..."),            ← dari joko
  AIMessage("Security: 3 router password default..."),      ← dari satria
  AIMessage("Laporan tersimpan: laporan/network-audit..."), ← dari budi
]

agent_log = [
  {source: "bambang", event_type: "routing", content: "→ monitor_agent [workflow]"},
  {source: "eko", event_type: "tool_call", content: "check_reachability(router_name='DTI')"},
  {source: "eko", event_type: "tool_result", content: "UNREACHABLE: timeout"},
  ... (semua tool calls dari semua agent)
  {source: "budi", event_type: "tool_call", content: "write_document(filename='network-audit...')"},
  {source: "budi", event_type: "tool_result", content: "Dokumen berhasil disimpan"},
]
```

---

## 6. Perbandingan Semua Pola

| Pola | Bambang LLM calls | Komunikasi data | Paralel | Bambang tahu alur | Kompleksitas kode |
|---|---|---|---|---|---|
| **Hub-and-Spoke** (sekarang) | N+1 (6 untuk 5 agent) | Implisit (teks) | ❌ | ✅ Penuh | Rendah |
| **Workflow Queue** | 2 | Implisit (teks) | ❌ | ✅ Saat planning | Sedang |
| **Command + Typed Handoff** | 1 | ✅ Eksplisit (typed) | ❌ | ❌ Kehilangan visibilitas | Sedang |
| **Send API (Fan-out)** | 1 | Implisit | ✅ | ✅ Saat planning | Tinggi |
| **Subgraph** | 1 | Terstruktur | ✅ (di dalam subgraph) | Partial | Tinggi |

### Rekomendasi Bertahap

```
Tahap 1 (Sekarang → Jangka Pendek):
  Implementasi Workflow Queue
  → Manfaat terbesar dengan perubahan paling minimal
  → Hemat 4x LLM call untuk audit komprehensif
  → Tidak mengubah cara agent bekerja secara internal

Tahap 2 (Jangka Menengah):
  Tambah field agent_handoff ke state
  → Komunikasi lebih terstruktur antar agent
  → Tidak harus pakai Command — cukup set field di state
  → Agent penerima bisa langsung baca data, tidak perlu parse teks

Tahap 3 (Jangka Panjang):
  Send API untuk agent yang independen (eko + satria paralel)
  → Perlu perancangan state yang lebih teliti (reducer)
  → Potensi penghematan waktu paling besar
```

---

## 7. Referensi Kode

### File yang Relevan untuk Implementasi

| Perubahan | File | Yang Perlu Diubah |
|---|---|---|
| Tambah `workflow_queue` ke state | `agent.py` | `NetworkOpsState` + `reset_agent` |
| Logic workflow di supervisor | `agents/nodes.py` | `supervisor_node` + prompt |
| Pop queue di specialist | `agents/nodes.py` | `_make_specialist_node` |
| Conditional edges dari specialist | `agents/graph.py` | `build_graph` |
| Tambah `agent_handoff` ke state | `agent.py` | `NetworkOpsState` |
| Command-based routing | `agents/nodes.py` | node functions yang relevan |
| Fan-out logic | `agents/nodes.py` | `supervisor_node` |

### Import yang Dibutuhkan

```python
# Untuk Command-based routing
from langgraph.types import Command

# Untuk parallel fan-out
from langgraph.types import Send

# Sudah ada (untuk human-in-the-loop)
from langgraph.types import interrupt
```

### Urutan Belajar yang Disarankan

```
1. Pahami state dulu → LANGGRAPH_FUNDAMENTALS.md
2. Implementasi Workflow Queue (pola paling mudah)
   → Eksperimen: kirim query "audit komprehensif", lihat bambang LLM calls berkurang
3. Tambah agent_handoff ke state
   → Eksperimen: lihat bagaimana agus merespons lebih tepat dengan data terstruktur
4. Eksplorasi Send API di environment test
   → Eksperimen: jalankan eko + satria paralel, ukur perbedaan waktu
```

---

*Dokumen ini bagian dari seri pembelajaran arsitektur llmnetops.*  
*Dokumen sebelumnya: [LANGGRAPH_FUNDAMENTALS.md](./LANGGRAPH_FUNDAMENTALS.md)*  
*Topik lanjutan: Implementasi Workflow Queue step-by-step*
