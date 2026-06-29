# Frontend Implementation Plan — NetOps AI Web Interface

**Versi:** 1.0  
**Tanggal:** 2026-06-29  
**Status:** Draft  
**Branch:** `feature/web-server`  
**Deployment:** Dockerized di `frontend/`

---

## 1. Tujuan

Membangun web interface untuk NetOps AI yang menggantikan TUI curses (`tui.py`) dengan pengalaman yang lebih accessible — mendukung multi-user, bisa diakses dari browser manapun di jaringan kampus, dan memudahkan konfigurasi/manajemen sistem.

### 1.1 Kenapa Web Interface

| Aspek | TUI (saat ini) | Web Interface |
|-------|---------------|---------------|
| Akses | Hanya dari terminal SSH ke server | Browser dari manapun |
| Multi-user | Satu sesi per terminal | Banyak operator simultan |
| Visualisasi | Teks monospace, terbatas curses | Chart, tabel interaktif, Markdown rendering |
| Konfigurasi | Edit file YAML manual | Form-based, validasi langsung |
| Mobile | Tidak bisa | Responsive |

### 1.2 Scope

Web interface mencakup **semua** kapabilitas TUI saat ini plus fitur manajemen yang sebelumnya dilakukan manual (edit config.yaml, manage skills, review pending skills, NetBox integration).

---

## 2. Current State — What Already Exists

### 2.1 Backend: `server.py` (Functional)

A FastAPI web server already exists at project root. It wraps `agent.py` public API over HTTP with SSE streaming.

**Existing endpoints:**

| Method | Endpoint | Deskripsi | Status |
|--------|----------|-----------|--------|
| `POST` | `/chat` | Send message, SSE stream response | Working |
| `POST` | `/approve` | Approve/reject pending action, SSE stream | Working |
| `GET` | `/info` | Model name + Ollama host | Working |
| `GET` | `/metrics?n=100` | Token usage (last N entries) | Working |
| `POST` | `/session/new` | Create new thread, return thread_id | Working |
| `GET` | `/` | Serve `frontend/index.html` | Working |

**SSE stream format** (current `server.py` output):
```
data: {"type": "routing", "content": "[bambang] → monitor_agent"}

data: {"type": "tool_call", "content": "[eko] get_interface_stats(router=\"DTI\")"}

data: {"type": "tool_result", "content": "[eko] ether1 UP 1Gbps ↑234Mbps..."}

data: {"type": "ai", "content": "Status jaringan kampus:\n..."}

data: {"type": "approval_required", "content": "{\"agent\":\"joko\",\"action\":\"backup\",\"risk_level\":\"medium\"}"}

: ping
```

**Key patterns already solved:**
- Async streaming wrapper (`_stream_events`) — runs sync `agent.stream_agent_response()` in threadpool, feeds events via `asyncio.Queue`, sends `:ping` heartbeats every 3s
- Session store — `_sessions` dict maps `thread_id → (graph, config)`
- CORS configured for `*`
- Static file serving for `frontend/fonts/` and `frontend/assets/`

**Run:**
```bash
python server.py
# or: uvicorn server:app --reload
```

### 2.2 Frontend Assets (Committed)

```
frontend/
├── index.html              ← Existing HTML prototype (static, sample data)
├── assets/
│   ├── glyph.svg           ← App icon glyph
│   └── logo.svg            ← App logo
└── fonts/
    ├── IBMPlexMono-Regular.woff2
    ├── IBMPlexMono-Medium.woff2
    ├── IBMPlexMono-SemiBold.woff2
    ├── IBMPlexSans-Regular.woff2
    ├── IBMPlexSans-Medium.woff2
    ├── IBMPlexSansCondensed-Medium.woff2
    └── IBMPlexSansCondensed-SemiBold.woff2
```

### 2.3 Dependencies (Already in requirements.txt)

```
fastapi>=0.115
uvicorn[standard]>=0.32
```

---

## 3. System Inventory

### 3.1 Agents (7 specialist + 1 supervisor)

| Agent | Alias | Domain | Key Capabilities |
|-------|-------|--------|-----------------|
| `supervisor` | bambang | orchestration | Route queries, skill matching, intent tracking |
| `monitor_agent` | eko | monitoring | Health check, traffic, reachability, DHCP overview |
| `diagnose_agent` | agus | diagnostics | OSPF/BGP troubleshoot, error analysis, RCA |
| `config_agent` | joko | configuration | Backup, write commands (needs approval), config read |
| `security_agent` | satria | security | Firewall audit, user accounts, brute-force detection |
| `document_agent` | budi | documentation | Reports, templates, skill authoring |
| `netbox_agent` | yanto | IPAM/DCIM | NetBox queries, drift detection, VLAN provisioning, BGP sync |
| `validasi_agent` | wati | validation | Verify action items, confirm issues, assess impact |

Agents can be **enabled/disabled** via `enabled: false` in their frontmatter.

### 3.2 Tools (52+ atomic functions)

#### SSH/Router Tools (original)

| Domain | Tools |
|--------|-------|
| **Monitoring** | `list_routers`, `check_reachability`, `check_ssh_access`, `get_system_info`, `get_interface_stats`, `get_interface_traffic`, `get_traffic_summary`, `get_top_talkers`, `get_queue_stats`, `get_traffic_all`, `get_top_interfaces_all` |
| **DHCP** | `get_dhcp_leases`, `get_router_leases`, `audit_dhcp`, `search_device` |
| **Routing** | `get_routing_full`, `get_router_config`, `get_bgp_sessions`, `get_ospf_neighbors` |
| **Config** | `run_command`, `run_command_all`, `run_command_write` (approval) |
| **Backup** | `backup_router_config` (approval), `list_backups`, `diff_config` |
| **Security** | `audit_security` |
| **Diagnostic** | `run_diagnostic`, `get_router_log` |
| **Document** | `write_document`, `list_templates`, `read_template`, `create_template`, `write_skill` |
| **Utility** | `list_routers`, `get_current_time`, `fetch_url` |

#### NetBox IPAM Tools (new on this branch)

| Tool | Type | Deskripsi |
|------|------|-----------|
| `get_netbox_devices` | read | List devices dari NetBox |
| `get_netbox_device_interfaces` | read | Interfaces per device |
| `get_netbox_device_ips` | read | IP addresses per device |
| `get_netbox_drift_report` | read | Compare NetBox vs router (actual) |
| `add_netbox_ip_address` | write | Tambah IP di NetBox |
| `update_netbox_interface` | write | Update interface di NetBox |
| `populate_netbox_from_router` | write | Sync router data → NetBox |
| `get_netbox_vlan_groups` | read | VLAN groups |
| `get_next_available_vlan` | read | Next available VLAN ID |
| `get_netbox_vlan_group_detail` | read | VLAN group detail |
| `create_netbox_vlan_interface` | write | Provision VLAN + interface |
| `populate_netbox_bgp` | write | Sync BGP sessions → NetBox |
| `get_netbox_bgp_drift` | read | BGP drift detection |
| `resolve_router_host` | read | Resolve router name → host IP |

#### Config YAML Tools (new on this branch)

| Tool | Deskripsi |
|------|-----------|
| `patch_router_host` | Update host IP di config.yaml |
| `patch_router_field` | Update any field di config.yaml |
| `add_router_to_config` | Tambah router baru ke config.yaml |
| `remove_router_from_config` | Hapus router dari config.yaml |

#### Agent Memory Tools (new on this branch)

| Tool | Deskripsi |
|------|-----------|
| `remember_router_fact` | Save fact tentang router (persists cross-session) |
| `recall_router_facts` | Recall facts untuk satu router |
| `recall_all_router_facts` | Recall semua facts |
| `forget_router_facts` | Hapus facts |

### 3.3 Skills (33+ active)

| Domain | Count | Key Skills |
|--------|-------|------------|
| monitoring | 8 | `network-health-check`, `morning-check`, `mtu-mismatch-diagnostics`, `capacity-planning`, `action-validation`, `netbox-read` |
| config | 8 | `config-backup`, `config-change`, `commissioning`, `netbox-sync`, `netbox-bgp-sync`, `router-discovery`, `router-to-netbox-sync`, `vlan-provisioning` |
| routing | 4 | `bgp-diagnostics`, `ospf-diagnostics`, `bgp-prefix-leak`, `static-route-management` |
| security | 3 | `security-audit`, `brute-force-response`, `firewall-management` |
| dhcp | 4 | `dhcp-client-diagnostics`, `dhcp-pool-audit`, `static-lease-management`, `utbk-session-monitoring` |
| documents | 2 | `document-writing`, `skill-authoring` |
| interface | 1 | `link-diagnostics` |
| maintenance | 1 | `router-maintenance` |
| global | 1 | `pedoman-agent` (global agent guidelines) |

### 3.4 NetworkOpsState

```python
class NetworkOpsState(TypedDict):
    messages:          Annotated[list, add_messages]
    next_agent:        str
    active_agent:      str
    injected_skills:   list[str]
    agent_log:         Annotated[list[AgentLogEntry], _append]
    pending_approval:  ApprovalRequest | None
    approval_decision: str | None
    original_intent:   str        # ← new: tracks user's original query across agent hops
```

### 3.5 Test Scenarios (17)

`tests/scenarios/*.yaml` — covers health-check, BGP/OSPF, DHCP, security, NetBox drift, NetBox BGP, NetBox VLAN provisioning, validation flows, greeting, config-direct, scope-idren.

---

## 4. Architecture

### 4.1 Deployment Overview

```
┌──────────────────────────────────────────────────────────┐
│  Docker Compose                                          │
│                                                          │
│  ┌──────────────┐        ┌────────────────────────┐     │
│  │   frontend   │  HTTP  │       backend          │     │
│  │   (Nginx +   │───────►│  (server.py + uvicorn) │     │
│  │   static SPA)│  :3000 │                  :8000 │     │
│  └──────────────┘        │                        │     │
│                          │   agent.py (public API) │     │
│                          │   tools/*.py (SSH)      │     │
│                          │   skills/ (hot reload)  │     │
│                          │   agents/ (LangGraph)   │     │
│                          └──┬─────────────┬───────┘     │
│                             │ SSH         │ HTTP         │
└─────────────────────────────┼─────────────┼─────────────┘
                              │             │
                     ┌────────▼──────┐  ┌───▼───────┐
                     │  MikroTik     │  │  NetBox   │
                     │  Routers      │  │  IPAM     │
                     │  (campus LAN) │  │  (HTTP)   │
                     └───────────────┘  └───────────┘
```

### 4.2 Directory Structure (Target)

```
frontend/
├── Dockerfile              ← Multi-stage: build SPA → serve via Nginx
├── docker-compose.yml      ← frontend + backend services
├── nginx.conf              ← Reverse proxy: /api/* → backend:8000
│
├── assets/                 ← (existing) glyph.svg, logo.svg
├── fonts/                  ← (existing) IBMPlex woff2 files
│
├── src/                    ← SPA source (new)
│   ├── index.html
│   ├── main.js             ← Entry point, router, app init
│   ├── api.js              ← HTTP + SSE client
│   ├── store.js            ← Reactive state management
│   │
│   ├── components/         ← Reusable UI components
│   │   ├── Sidebar.js
│   │   ├── Header.js
│   │   ├── Footer.js
│   │   ├── AgentCard.js
│   │   ├── ApprovalModal.js
│   │   └── ...
│   │
│   ├── screens/            ← One file per screen/page
│   │   ├── Dashboard.js
│   │   ├── Chat.js
│   │   ├── NetworkMonitor.js
│   │   ├── DhcpMonitor.js
│   │   ├── NetBox.js
│   │   ├── Skills.js
│   │   ├── Reports.js
│   │   ├── Backups.js
│   │   ├── Metrics.js
│   │   └── Settings.js
│   │
│   └── styles/
│       └── theme.css       ← Design tokens (CSS custom properties)
│
└── backend/                ← (not needed — server.py is at project root)
```

### 4.3 Backend Strategy

`server.py` already handles the core chat/approve/metrics/session flow. It needs **extension** (not replacement) with additional API routes for dashboard data, skills management, config CRUD, and NetBox integration.

Two approaches:

**Option A (recommended): Extend `server.py` in-place**
- Add route modules as functions in `server.py` or import from a `routes/` package
- Keeps deployment simple: one FastAPI app, one process
- `server.py` already has the session store and agent imports

**Option B: Separate backend service**
- New `frontend/backend/main.py` imports from project root
- More Docker complexity, but cleaner separation
- Only needed if backend needs different Python environment

---

## 5. Backend API Design — New Endpoints

Endpoints below extend the existing `server.py`. The chat/approve/metrics/session endpoints are already implemented.

### 5.1 Status & System Info

| Method | Endpoint | Deskripsi | Maps to |
|--------|----------|-----------|---------|
| `GET` | `/api/status` | Full agent status | `agent.get_agent_status()` |
| `GET` | `/api/skills` | List all skills (enabled + disabled) | `agent.get_available_skills()` + all |
| `GET` | `/api/agents` | List agent definitions | `_agent_loader.all()` |

```python
@app.get("/api/status")
def status():
    st = _agent.get_agent_status()
    st["agents"] = [
        {"name": d.name, "alias": d.alias, "description": d.description,
         "model": d.model, "enabled": d.enabled, "tools_count": len(d.tools)}
        for d in _agent_loader.all()
    ]
    st["skills_count"] = len(_agent._skill_lib)
    return st
```

### 5.2 Direct Tool Invocation (Dashboard)

Tools dipanggil langsung tanpa melalui agent — untuk dashboard real-time.

| Method | Endpoint | Deskripsi | Maps to |
|--------|----------|-----------|---------|
| `GET` | `/api/tools/routers` | Daftar router | `list_routers.invoke({})` |
| `POST` | `/api/tools/reachability` | Ping satu router | `check_reachability.invoke()` |
| `POST` | `/api/tools/reachability/all` | Ping semua router paralel | loop `check_reachability` |
| `POST` | `/api/tools/system-info` | CPU/RAM/uptime | `get_system_info.invoke()` |
| `POST` | `/api/tools/traffic` | Traffic satu interface | `get_interface_traffic.invoke()` |
| `POST` | `/api/tools/traffic/all` | Traffic semua router | `get_traffic_all.invoke({})` |
| `POST` | `/api/tools/dhcp/audit` | Audit DHCP semua router | `audit_dhcp.invoke({})` |
| `POST` | `/api/tools/dhcp/search` | Cari device by IP/MAC | `search_device.invoke()` |
| `POST` | `/api/tools/security/audit` | Audit security satu router | `audit_security.invoke()` |
| `POST` | `/api/tools/diagnostic` | Ping/traceroute dari router | `run_diagnostic.invoke()` |
| `GET` | `/api/tools/router-log` | Log router | `get_router_log.invoke()` |

```python
from agents.tools import TOOL_MAP

@app.get("/api/tools/routers")
def get_routers():
    return {"result": TOOL_MAP["list_routers"].invoke({})}

@app.post("/api/tools/reachability")
def check_reach(body: RouterBody):
    return {"result": TOOL_MAP["check_reachability"].invoke({"router_name": body.router_name})}
```

### 5.3 NetBox Integration

| Method | Endpoint | Deskripsi | Maps to |
|--------|----------|-----------|---------|
| `GET` | `/api/netbox/devices` | List NetBox devices | `get_netbox_devices.invoke()` |
| `GET` | `/api/netbox/devices/{name}/interfaces` | Interfaces | `get_netbox_device_interfaces.invoke()` |
| `GET` | `/api/netbox/devices/{name}/ips` | IPs | `get_netbox_device_ips.invoke()` |
| `GET` | `/api/netbox/drift/{name}` | Drift report | `get_netbox_drift_report.invoke()` |
| `GET` | `/api/netbox/vlans` | VLAN groups | `get_netbox_vlan_groups.invoke()` |
| `GET` | `/api/netbox/bgp/drift` | BGP drift | `get_netbox_bgp_drift.invoke()` |

### 5.4 Skills Management

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/api/skills` | List semua skills (enabled + disabled) |
| `GET` | `/api/skills/{name}` | Detail skill + body Markdown |
| `PUT` | `/api/skills/{name}` | Update skill (frontmatter + body) |
| `POST` | `/api/skills` | Buat skill baru |
| `DELETE` | `/api/skills/{name}` | Delete skill |
| `GET` | `/api/skills/pending` | List pending skills (`skills/.pending/`) |
| `POST` | `/api/skills/pending/{name}/approve` | Approve pending |
| `POST` | `/api/skills/pending/{name}/reject` | Reject pending |

### 5.5 Configuration Management

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/api/config/routers` | Router list dari config.yaml |
| `POST` | `/api/config/routers` | Add router | 
| `PUT` | `/api/config/routers/{name}` | Update router |
| `DELETE` | `/api/config/routers/{name}` | Remove router |
| `GET` | `/api/config/agents` | Agent definitions list |
| `GET` | `/api/config/agents/{name}` | Agent definition detail |
| `PUT` | `/api/config/agents/{name}` | Update agent definition |
| `POST` | `/api/config/agents/{name}/toggle` | Enable/disable agent |
| `GET` | `/api/config/env` | Non-sensitive env settings |
| `PUT` | `/api/config/env` | Update OLLAMA_BASE_URL, OLLAMA_MODEL |

Note: Router config CRUD can reuse the existing `config_yaml.py` tools internally:
```python
@app.post("/api/config/routers")
def add_router(body: RouterConfigBody):
    from tools.config_yaml import add_router_to_config
    result = add_router_to_config.invoke({
        "name": body.name, "host": body.host,
        "ros_version": body.ros_version,
    })
    return {"result": result}
```

### 5.6 Reports & Backups

| Method | Endpoint | Maps to |
|--------|----------|---------|
| `GET` | `/api/reports` | `list_reports.invoke({})` |
| `GET` | `/api/reports/{filename}` | `get_report.invoke()` |
| `GET` | `/api/reports/{filename}/toc` | `get_report_toc.invoke()` |
| `GET` | `/api/backups` | `list_backups.invoke({})` |
| `GET` | `/api/backups/diff` | `diff_config.invoke()` |
| `GET` | `/api/templates` | `list_templates.invoke({})` |

### 5.7 Agent Memory

| Method | Endpoint | Maps to |
|--------|----------|---------|
| `GET` | `/api/memory` | `recall_all_router_facts.invoke({})` |
| `GET` | `/api/memory/{router}` | `recall_router_facts.invoke()` |
| `DELETE` | `/api/memory/{router}` | `forget_router_facts.invoke()` |

---

## 6. Frontend Screens

### 6.1 Screen Map

| # | Screen | Path | Deskripsi |
|---|--------|------|-----------|
| 1 | Dashboard | `/` | System overview: agent status, router grid, recent reports |
| 2 | AI Chat | `/chat` | Multi-agent chat with SSE streaming + approval modal |
| 3 | Network Monitor | `/network` | Router status, traffic, reachability, top talkers |
| 4 | DHCP Monitor | `/dhcp` | Pool utilization, device search, lease browser |
| 5 | NetBox | `/netbox` | Device inventory, drift detection, VLAN management |
| 6 | Skills | `/skills` | Browse, edit, create, review pending |
| 7 | Reports | `/reports` | Markdown viewer + TOC |
| 8 | Backups | `/backups` | List per router + diff viewer |
| 9 | Metrics | `/metrics` | Token usage per agent |
| 10 | Settings | `/settings` | Routers, agents, environment config |

### 6.2 Screen Details

#### 6.2.1 Dashboard (`/`)

```
┌─────────────────────────────────────────────────────────────┐
│  NETOPS AI          Campus Network Operations    ● IDLE     │
├────────┬────────────────────────────────────────────────────┤
│ Menu   │                                                    │
│        │  ┌─ System ──────────┐  ┌─ Router Status ────────┐│
│ ● Dash │  │ Model: qwen3.5:9b│  │ DTI      10.10.1.1  ✓ ││
│   Chat │  │ Skills: 33 loaded │  │ FIKES    10.10.2.1  ✗ ││
│   Net  │  │ Agents: 7 (6 on) │  │ LIBRARY  10.10.3.1  ✓ ││
│   DHCP │  │ Ollama: ✓ online  │  │ REKTORAT 10.10.4.1  ✓ ││
│   NBox │  │ NetBox: ✓ online  │  └────────────────────────┘│
│   Skill│  └───────────────────┘                             │
│   Reprt│  ┌─ Agent Registry ──────────────────────────────┐│
│   Back │  │ bambang(super) eko(mon) agus(diag) joko(cfg)  ││
│   Metr │  │ satria(sec) budi(doc) yanto(nbox) wati(val)   ││
│   Sett │  └───────────────────────────────────────────────┘│
└────────┴────────────────────────────────────────────────────┘
```

#### 6.2.2 AI Chat (`/chat`)

```
┌────────────────────────────────────────────┬──────────────┐
│  AI Chat     Thread: [session-abc ▾]       │ Agent Status │
│                                            │              │
│  ┌─ ANDA ─────────────── 14:32:00 ───┐    │ ● BAMBANG    │
│  │ cek status jaringan kampus         │    │   supervisor │
│  └────────────────────────────────────┘    │   ✓ SELESAI  │
│                                            │              │
│  ┌─ AGENT ────────────── 14:32:01 ───┐    │ ● EKO        │
│  │ → [bambang] routing → eko          │    │   monitor    │
│  │ ⚙ [eko] get_interface_stats(DTI)   │    │   ▶ RUNNING  │
│  │ ✓ [eko] 12 interfaces retrieved    │    │              │
│  │                                    │    │ ○ AGUS       │
│  │ Status jaringan kampus:            │    │ ○ JOKO       │
│  │ (rendered Markdown)                │    │ ○ SATRIA     │
│  └────────────────────────────────────┘    │ ○ BUDI       │
│                                            │ ○ YANTO      │
│  ┌────────────────────────────────────┐    │ ○ WATI       │
│  │ › ketik pertanyaan...     [SEND]  │    └──────────────┘
│  └────────────────────────────────────┘
```

SSE client consumes existing `POST /chat` format:
```javascript
async function sendMessage(threadId, message, onEvent) {
    const res = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({thread_id: threadId, message}),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split('\n\n');
        buffer = lines.pop();
        for (const block of lines) {
            if (block.startsWith('data: ')) {
                const payload = JSON.parse(block.slice(6));
                onEvent(payload.type, payload.content);
            }
        }
    }
}
```

#### 6.2.3 Network Monitor (`/network`)

Router grid + traffic + interface stats + top talkers. Data from direct tool invocation API.

#### 6.2.4 DHCP Monitor (`/dhcp`)

Pool utilization bars, device search form, lease table per router/server.

#### 6.2.5 NetBox (`/netbox`) — New

```
┌─────────────────────────────────────────────────────────────┐
│  NetBox Integration                    [⟳ Refresh]          │
│                                                             │
│  ┌─ Devices ──────────────────────────────────────────────┐│
│  │ Name        Site     Role       Status   Interfaces IP ││
│  │ DTI         Kampus   Router     Active   24         12 ││
│  │ FIKES       Kampus   Router     Active   16          8 ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─ Drift Detection ─────────────────────────────────────┐│
│  │ DTI: 3 drifts detected                                ││
│  │   ether1: NetBox says 10.39.1.1/24, router has none   ││
│  │   ether5: missing from NetBox                         ││
│  │   [Sync to NetBox]                                    ││
│  ├────────────────────────────────────────────────────────┤│
│  │ BGP Drift: 1 session mismatch                         ││
│  │   AS65001: NetBox says active, router shows idle      ││
│  └────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─ VLAN Groups ──────────────────────────────────────────┐│
│  │ Kampus-VLANs: 45 VLANs, next available: 146          ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 6.2.6 Skills (`/skills`)

Browse all 33+ skills, filter by domain, edit with Markdown editor, review pending skills from `skills/.pending/`.

#### 6.2.7 Settings (`/settings`)

Tabs: **Routers** | **Agents** | **Environment** | **NetBox** | **Memory**

- **Routers:** CRUD via `config_yaml.py` tools (already exist)
- **Agents:** View/edit definitions, toggle enable/disable
- **Environment:** OLLAMA_BASE_URL, OLLAMA_MODEL
- **NetBox:** Connection settings (URL, token per instance)
- **Memory:** View/clear agent memory facts per router

---

## 7. Design System

### 7.1 Typography (fonts already committed)

| Usage | Font | File |
|-------|------|------|
| Body text, code | IBM Plex Mono | `fonts/IBMPlexMono-*.woff2` |
| UI labels, navigation | IBM Plex Sans | `fonts/IBMPlexSans-*.woff2` |
| Headers, badges | IBM Plex Sans Condensed | `fonts/IBMPlexSansCondensed-*.woff2` |

### 7.2 Color Tokens

```css
:root {
  /* Backgrounds */
  --bg-primary:    #0a0f1a;
  --bg-secondary:  #111827;
  --bg-elevated:   #1a2332;
  --bg-hover:      #1f2d3d;

  /* Status */
  --color-success: #10b981;     /* UP, healthy, done */
  --color-warning: #f59e0b;     /* waiting, approval, degraded */
  --color-danger:  #ef4444;     /* DOWN, failed, error */
  --color-info:    #3b82f6;     /* routing, queued */

  /* Text */
  --text-primary:  #e2e8f0;
  --text-secondary:#94a3b8;
  --text-muted:    #475569;

  /* Accent */
  --accent:        #06b6d4;     /* cyan — links, active states */
  --accent-dim:    rgba(6, 182, 212, 0.15);

  /* Borders */
  --border:        rgba(148, 163, 184, 0.1);
  --border-active: rgba(6, 182, 212, 0.4);

  /* Fonts */
  --font-mono: 'IBM Plex Mono', monospace;
  --font-sans: 'IBM Plex Sans', system-ui, sans-serif;
  --font-condensed: 'IBM Plex Sans Condensed', sans-serif;
}
```

### 7.3 Agent States (8 agents)

| State | Color | Indicator |
|-------|-------|-----------|
| `standby` | muted | dim dot |
| `queued` | info/blue | solid dot |
| `running` | success/green | pulsing dot |
| `waiting` | warning/amber | blinking dot |
| `done` | secondary | static dimmed |
| `failed` | danger/red | static dot |
| `nonaktif` | muted | strikethrough (agent disabled) |

### 7.4 Layout

```
┌─ Header ─────────────────────────────────────── 48px ─┐
│  Logo  │  Title            │  Status pill │  Clock    │
├─ Body ─────────────────────────────────── flex: 1 ────┤
│ Sidebar│  Main Content                │  Right Panel  │
│  200px │                              │  (chat only)  │
│        │                              │   220px       │
│ Nav    │                              │  8 agent cards│
├─ Footer ─────────────────────────────────────── 32px ─┤
│  CTX%  │  PRED%  │  TOOLS  │  TIME  │  State         │
└───────────────────────────────────────────────────────┘
```

---

## 8. Docker Configuration

### 8.1 docker-compose.yml

```yaml
services:
  backend:
    build:
      context: ..
      dockerfile: frontend/Dockerfile.backend
    ports:
      - "8000:8000"
    volumes:
      - ../config.yaml:/app/config.yaml
      - ../.env:/app/.env:ro
      - ../backups:/app/backups
      - ../laporan:/app/laporan
      - ../data:/app/data
      - ../skills:/app/skills
      - ../agents/definitions:/app/agents/definitions
    environment:
      - PYTHONUNBUFFERED=1
    networks:
      - netops
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - netops
    restart: unless-stopped

networks:
  netops:
    driver: bridge
```

### 8.2 Backend Dockerfile (`Dockerfile.backend`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.3 Frontend Dockerfile

```dockerfile
FROM nginx:alpine

COPY src/ /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
COPY fonts/ /usr/share/nginx/html/fonts/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

### 8.4 Nginx Config

```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy existing endpoints (server.py)
    location ~ ^/(chat|approve|info|metrics|session) {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }

    # Proxy new API endpoints
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

### 8.5 Ollama Connectivity from Docker

```yaml
backend:
  extra_hosts:
    - "host.docker.internal:host-gateway"  # Ollama on host
  environment:
    - OLLAMA_BASE_URL=http://host.docker.internal:11434
    # Or remote: OLLAMA_BASE_URL=http://rogbox.local.id:11434
```

---

## 9. Key Implementation Notes

### 9.1 SSE Streaming is Already Solved

`server.py` has a production-ready async SSE wrapper (`_stream_events`) that:
- Runs the sync `agent.stream_agent_response()` in a threadpool
- Feeds events via `asyncio.Queue` with `call_soon_threadsafe`
- Sends `:ping` heartbeat every 3s to keep connections alive
- Handles `approval_required` events correctly

Frontend just needs to parse `data: {"type": "...", "content": "..."}` lines.

### 9.2 Thread Safety

- `SkillLibrary` — thread-safe (`threading.Lock`)
- `SqliteSaver` — `check_same_thread=False`
- `memory.db` — separate SQLite, `check_same_thread=False`
- `config.yaml` writes (via `config_yaml.py`) — need mutex in backend for concurrent requests
- SSH tools — stateless, safe for parallel calls

### 9.3 Parsing Tool Output

Tools return plain text strings. For dashboard structured data, parse in backend:
```python
@app.post("/api/tools/system-info")
def system_info(body: RouterBody):
    raw = TOOL_MAP["get_system_info"].invoke({"router_name": body.router_name})
    parsed = _parse_system_info(raw)  # extract CPU%, RAM%, uptime
    return {"raw": raw, "parsed": parsed}
```

### 9.4 Hot Reload in Docker

- `skills/` mounted as volume → `SkillLibrary` watchdog (`watchfiles`) detects changes
- `agents/definitions/` mounted → need manual reload via `_agent_loader.reload()`
- Add `POST /api/config/agents/reload` endpoint

### 9.5 Agent Enable/Disable

This branch supports `enabled: false` in agent definition frontmatter. The web Settings page can toggle this by rewriting the frontmatter.

### 9.6 NetBox Requires config.yaml

NetBox tools read connection info from `config.yaml`:
```yaml
netbox:
  kampus:
    url: https://netbox.kampus.ac.id
    token: YOUR_TOKEN
  idren:
    url: https://netbox.idren.id
    token: YOUR_TOKEN
```

---

## 10. Security Considerations

### 10.1 Do NOT Expose

| Data | Handling |
|------|----------|
| SSH passwords from config.yaml | Strip before response |
| NetBox tokens from config.yaml | Strip before response |
| `.env` raw file | Expose only non-sensitive values |
| `export sensitive` command | Blocked by `_BLOCKED_KEYWORDS` |
| Router config with passwords | Only via agent chat |

### 10.2 Authentication (Future)

Current: no auth (same as TUI). For production:
- HTTP Basic Auth at Nginx level (simplest)
- Or: FastAPI JWT middleware
- Roles: `operator` (full) vs `viewer` (read-only, no approval/write)

---

## 11. Implementation Phases

### Phase 1: Wire Chat to Backend
**Target:** Chat functional end-to-end via browser.

1. Build SPA shell: Header, Sidebar, Footer, screen router
2. Build Chat screen: message list, input, SSE streaming, 8-agent sidebar, approval modal
3. Wire to existing `POST /chat`, `POST /approve`, `POST /session/new`
4. Docker compose: backend (server.py) + Nginx serving SPA
5. Test: full chat → agent → SSH → response in browser

### Phase 2: Network Dashboard + DHCP
**Target:** Real-time monitoring without AI chat.

1. Add `/api/tools/*` routes to `server.py`
2. Build Network Monitor screen (router grid, traffic, top talkers)
3. Build DHCP Monitor screen (pool utilization, device search)
4. Auto-refresh toggle

### Phase 3: NetBox Integration Screen
**Target:** Visual NetBox management.

1. Add `/api/netbox/*` routes to `server.py`
2. Build NetBox screen (devices, drift detection, VLAN groups)
3. Sync actions (populate from router, resolve drifts)

### Phase 4: Skills & Reports
**Target:** Manage skills and view reports from web.

1. Add `/api/skills/*` routes (CRUD + pending review)
2. Build Skills screen (browse, filter, edit, review pending)
3. Add `/api/reports/*` routes
4. Build Reports screen (Markdown viewer + TOC)

### Phase 5: Configuration & Settings
**Target:** Full management — no more manual file editing.

1. Add `/api/config/*` routes (uses `config_yaml.py` tools)
2. Build Settings screen (Routers, Agents, Environment, NetBox, Memory tabs)
3. Add `/api/backups/*` routes
4. Build Backups screen (list + diff viewer)

### Phase 6: Metrics, Auth & Polish
**Target:** Production-ready.

1. Build Metrics screen (token usage charts per agent)
2. Add authentication
3. Responsive design
4. Error handling & loading states
5. Toast notifications for real-time events
