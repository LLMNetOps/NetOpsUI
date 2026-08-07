# Google Stitch Prompt Guide — LLMNetOps Web UI

Use these prompts at https://stitch.withgoogle.com/ to generate the LLMNetOps web interface screens. Each section is a self-contained prompt. Copy-paste one at a time.

---

## Brand Reference

**Colors extracted from logo:**
- **Navy (primary):** `#1B3A5C` — hex icon background, "LLM" text
- **Coral/Salmon (accent):** `#E88B6A` — "NetOps" text
- **White:** `#FFFFFF` — icon nodes/lines

**Extended palette (light enterprise theme):**
- Page background: `#F5F7FA` (cool gray)
- Card / surface: `#FFFFFF` (white)
- Sidebar: `#1B3A5C` (navy, same as logo)
- Sidebar text: `#FFFFFF` / `rgba(255,255,255,0.7)`
- Header: `#FFFFFF` with bottom border
- Text primary: `#1A202C` (near-black)
- Text secondary: `#64748B` (slate gray)
- Text muted: `#94A3B8`
- Accent / CTA: `#E88B6A` (coral from logo)
- Accent hover: `#D47A5A`
- Link / interactive: `#1B3A5C` (navy)
- Border: `#E2E8F0`
- Success: `#059669` (green)
- Warning: `#D97706` (amber)
- Danger: `#DC2626` (red)
- Info: `#2563EB` (blue)

---

## Prompt 1 — App Shell (Layout + Navigation)

```
Design a professional light-themed enterprise web application called "LLMNetOps" for campus network operations powered by AI agents. The look and feel should be similar to AWS Console or Google Cloud Console — clean, data-dense, premium, corporate.

Layout structure:

- Fixed top header bar (56px height, white background, subtle bottom border #E2E8F0):
  Left: Logo text "LLMNetOps" where "LLM" is bold navy #1B3A5C and "NetOps" is coral #E88B6A. 
  Center-right: breadcrumb showing current page. 
  Far right: status indicator (small green dot + "System Online" text), a notification bell icon, and user avatar circle with initials.

- Left sidebar (240px width, navy #1B3A5C background, white text):
  Top: small hexagonal network icon in white, app name below in white.
  Navigation items vertically stacked, each with an icon and label:
    Dashboard, AI Chat, Network, DHCP, NetBox, Skills, Reports, Backups, Metrics, Settings
  Active item has a white left border bar (3px), slightly brighter background rgba(255,255,255,0.1), and white text. Inactive items are rgba(255,255,255,0.65).
  Section dividers with small uppercase labels like "MONITORING", "MANAGEMENT", "SYSTEM".
  Bottom of sidebar: collapsed system info — model name, skills count in small muted white text.

- Main content area: light gray background #F5F7FA, content in white cards with 1px border #E2E8F0 and border-radius 8px.

- No footer bar (AWS console style — status lives in header).

Typography: IBM Plex Sans for UI text, IBM Plex Mono for code and data values. Clean, corporate, high information density. No playful elements. Generous whitespace between cards, tight spacing within cards.
```

---

## Prompt 2 — Dashboard Screen

```
Design the Dashboard screen for "LLMNetOps", a light-themed enterprise network operations web app. Page background #F5F7FA, cards are white with 1px border #E2E8F0 and border-radius 8px. Navy sidebar on the left is already designed.

Content area layout — responsive card grid with comfortable spacing (24px gap):

Card 1 — "System Overview" (top-left, spans 1 column):
- Vertical stat rows, each with a label and value:
  - LLM Model: "qwen3.5:9b" (monospace, medium weight)
  - Active Skills: "33" with small green badge
  - Agents: "7 registered, 6 active" 
  - Ollama: green dot + "Connected"
  - NetBox: green dot + "Connected"
- Clean divider lines between each row

Card 2 — "Router Health" (top-right, spans 1 column):
- Compact table: Router Name (bold), Host IP (monospace), Status badge
- Status badges: green pill "UP" or red pill "DOWN" 
- 6-8 rows
- Bottom: coral #E88B6A outline button "Ping All Routers"

Card 3 — "Agent Registry" (middle row, full width):
- Horizontal flex row of 8 compact agent cards:
  - Each card: white background, subtle border, small padding
  - Agent alias in uppercase bold (BAMBANG, EKO, AGUS, JOKO, SATRIA, BUDI, YANTO, WATI)
  - Role label below in small gray text: supervisor, monitor, diagnosa, config, security, dokumen, netbox, validasi
  - Small colored status dot: green (active), gray (standby), strikethrough for disabled
  - Cards have subtle shadow on hover

Card 4 — "Recent Reports" (bottom-left):
- List of 4-5 files with icon, filename, date (e.g. "May 10, 2026"), and size
- Clickable rows with hover highlight
- "View All →" link at bottom in navy

Card 5 — "Quick Actions" (bottom-right):
- Grid of 4 action buttons with icons:
  "Health Check", "Security Audit", "Backup All", "DHCP Audit"  
- Buttons: white background, navy text, 1px border #E2E8F0, hover fills with light coral tint
- Each button has a small icon on the left

Overall: clean, structured, looks like a cloud console dashboard. No dark backgrounds.
```

---

## Prompt 3 — AI Chat Screen

```
Design an AI Chat interface for "LLMNetOps", a light-themed enterprise multi-agent network operations platform. This is the core screen. Think of it like a professional Slack-meets-terminal hybrid.

Page background #F5F7FA. Navy sidebar on left already designed.

Layout has 2 main areas:
- Center (flex: 1): Chat conversation area
- Right (260px): Agent status panel, white card with border

CENTER — Chat area:
- Top bar: white background, "AI Chat" title in navy bold, thread selector dropdown (shows thread ID), "New Thread" button (coral outline), "Clear Chat" button (gray outline).
- Message area: white background card, scrollable, takes most height.

  User message: 
  - Left-aligned, full width
  - Small "ANDA" label in navy #1B3A5C uppercase + timestamp in gray on the right
  - Message text below in dark text, normal weight
  - Light top border to separate from previous message

  Agent response group:
  - Small "AGENT" label in coral #E88B6A uppercase + timestamp
  - Streaming event rows — each is a compact single line with:
    - Routing: "→" icon in amber, text "[bambang] → eko/monitor_agent" in amber-brown
    - Tool call: "⚙" icon in navy, text "[eko] get_interface_stats(router='DTI')" in navy
    - Tool result: "✓" icon in green, preview text in gray
    - Error: "✗" icon in red
  - Events have a very light gray background #F8FAFC to distinguish from the final response
  - Final AI text: regular dark text, properly formatted with paragraphs and bullet points
  - While streaming: three bouncing gray dots animation

- Bottom input area: white card with top border. Contains:
  - Text input field: white background, 1px border #E2E8F0, focus border coral #E88B6A
  - "Send" button: solid coral #E88B6A with white text, right side of input
  - Hint line below in small gray: "[Enter] Kirim · [Ctrl+L] Clear"

RIGHT — Agent Status Panel:
- White card with header "Agent Status" in uppercase small gray text
- 8 stacked mini-cards, one per agent:
  - Alias in bold (EKO), role in small gray (monitor)
  - Status: colored dot + label: "STANDBY" (gray), "RUNNING" (green), "WAITING" (amber), "DONE" (green dimmed), "FAILED" (red)
  - Running agents have a subtle green left border
  - Detail line: last tool called in small monospace
- Bottom: "Active Query" section with the current question and elapsed time

Overall feel: enterprise chat tool. Light, clean, professional. Not a toy chatbot.
```

---

## Prompt 4 — Approval Modal

```
Design a modal dialog for "LLMNetOps" (light enterprise theme) that appears when an AI agent requires operator approval before executing a risky action.

Overlay: semi-transparent white-gray background rgba(0, 0, 0, 0.3) with subtle backdrop blur.

Modal: white card, max-width 500px, centered, border-radius 8px, subtle shadow (0 4px 24px rgba(0,0,0,0.12)).

Top section:
- Warning banner at top: amber #FEF3C7 background strip with amber icon and text "Approval Required" in dark amber #92400E, uppercase, bold.

Content:
- Field rows in a clean form-like layout (label on left in gray uppercase small text, value on right in dark text):
  - Agent: "joko / config_agent"
  - Action: "backup_router_config('DTI')" in monospace
  - Router: "DTI (10.39.0.1)"
  - Risk Level: "MEDIUM" in amber badge pill, or "HIGH" in red badge pill
  - Description: "Export full configuration to backups/DTI/"

Bottom: 
- Two buttons aligned right with 12px gap:
  - "Reject" — white background, red #DC2626 text and border, hover fills light red
  - "Approve" — solid green #059669 background, white text, hover darkens
- Subtle hint text below buttons: "Keyboard: Y = Approve, N = Reject"

The modal should feel authoritative and serious — like a cloud console's "are you sure you want to delete this resource?" dialog, not a casual popup.
```

---

## Prompt 5 — Network Monitor Screen

```
Design a Network Monitor screen for "LLMNetOps", light enterprise theme. Page background #F5F7FA, white cards with border.

Top controls bar: 
- Page title "Network Monitor" in navy bold
- Right side: auto-refresh toggle switch with interval dropdown (30s, 60s, 5m), "Refresh Now" coral outline button

Section 1 — "Router Overview" (white card, full width):
- Clean data table with:
  - Column headers in uppercase small gray text with sort arrows
  - Columns: Router Name (bold navy), Host IP (monospace), Status (colored pill badge: green "UP" / red "DOWN"), RTT (monospace), CPU % (with inline mini progress bar), RAM % (with inline mini progress bar), Uptime
  - Alternating row colors: white and #F8FAFC
  - 8 rows of sample data
  - Clickable rows to select router for detail panels below

Section 2 — Two white cards side by side (below router table):

Left card — "Traffic — [DTI]" (router name from selection):
- Dropdown at top to switch router
- Interface list rows:
  - Interface name (bold): "ether1"
  - Upload: "↑ 234 Mbps" in navy
  - Download: "↓ 89 Mbps" in navy  
  - Small horizontal stacked bar showing TX (coral) vs RX (navy) proportions
  - DOWN interfaces shown with red text and red left border

Right card — "Interface Health — [DTI]":
- Table: Interface, RX Errors, TX Errors, RX Drops, TX Drops
- Zero values in gray, non-zero in amber bold, high values in red bold
- DOWN interfaces have red status indicator

Section 3 — "Top Talkers" (white card, full width):
- Two columns layout within the card:
  - Left: "Top Upload" — 5 rows: IP address + bandwidth bar + Mbps value
  - Right: "Top Download" — same format
  - Bars use coral for upload, navy for download

AWS-console style data tables: clean headers, alternating rows, inline status badges.
```

---

## Prompt 6 — DHCP Monitor Screen

```
Design a DHCP Monitor screen for "LLMNetOps", light enterprise theme. Background #F5F7FA.

Section 1 — "Pool Utilization" (white card):
- Clean table with columns: Router (bold), DHCP Server (monospace), Used, Total, Utilization
- Last column has a horizontal progress bar:
  - Green fill for <60%
  - Amber fill for 60-85%  
  - Red fill for >85%
- Percentage text overlaid on or beside the bar
- Example: "DTI / dhcp-lab-tik / 142 / 200 / 71%"

Section 2 — "Device Search" (white card):
- Label: "Find device by IP or MAC address"
- Search input field (wide, with search icon inside) + coral "Search" button
- Results below in a detail card when found:
  - Two-column layout: label (gray) / value (dark) pairs
  - IP Address, MAC Address, Router, DHCP Server, Hostname, Status (green "bound" pill or amber "waiting" pill), Lease Time Remaining
  - If not found: subtle red alert "Device not found"

Section 3 — "Lease Browser" (white card):
- Top: two dropdown selectors — Router and DHCP Server
- Data table below: IP (monospace), MAC Address (monospace), Hostname, Status (pill badge), Last Seen
- Pagination at bottom: "Showing 1-20 of 142" with page buttons
- Table rows have alternating background

Clean corporate data layout. Monospace for IP and MAC values.
```

---

## Prompt 7 — NetBox Integration Screen

```
Design a NetBox IPAM integration screen for "LLMNetOps", light enterprise theme. Background #F5F7FA.

Top: page title "NetBox Integration" with instance selector dropdown (values: "kampus", "idren") and connection status indicator (green dot + "Connected").

Section 1 — "Devices" (white card):
- Table: Device Name (bold navy link), Site, Role (badge pill), Platform, Status (green "Active" or gray "Planned" pill), Interfaces, IPs
- Rows clickable to expand and show interface detail inline

Section 2 — "Configuration Drift" (white card, this is the key feature):
- Header with icon: "Drift Detection" + summary text "3 drifts across 2 devices"
- If drifts exist: subtle amber left-border on the card
- Each drift item as a row:
  - Left: Router name + interface name in bold
  - Center: Two-column comparison:
    "NetBox: 10.39.1.1/24" vs "Router: (not configured)" 
    with arrows between them
  - Right: drift type badge (amber "IP Mismatch", red "Missing from NetBox", blue "Extra on Router")
  - Action: small "Sync" link button per item
- Top right: "Sync All to NetBox" coral button
- Sub-card below: "BGP Session Drift" — similar format for BGP mismatches showing AS numbers, session states

Section 3 — "VLAN Groups" (white card):
- Table: Group Name, VLAN Count, ID Range, Next Available
- Expandable rows showing individual VLANs within each group
- "Provision New VLAN" button (coral outline)

Status colors: green "In Sync" badge, amber "Drift Detected" badge, red "Missing" badge.
Clean enterprise look — this should feel like an AWS resource management page.
```

---

## Prompt 8 — Skills Management Screen

```
Design a Skills management screen for "LLMNetOps", light enterprise theme. Background #F5F7FA.

Top bar: Page title "Skills" with count badge "(33 active)" in gray, buttons: "+ New Skill" (coral solid), "Reload" (gray outline with refresh icon).

Filter bar: horizontal row of clickable pill/chip buttons for domain filtering:
All (33), monitoring (8), config (8), routing (4), security (3), dhcp (4), documents (2), interface (1), maintenance (1)
Active filter: coral #E88B6A filled pill with white text. Inactive: white pill with gray border.

Skill list — white card containing vertical list of skill items:
Each skill row (separated by light border):
- Left column: 
  - Skill name in bold navy: "network-health-check"
  - Domain as small colored badge pill below: "monitoring" in coral
  - Trigger keywords in small gray italic: "cek status, health check, status jaringan"
- Right column:
  - Green "ACTIVE" badge (or gray "DISABLED" badge)
  - Tool count: "5 tools" in small text
  - Approval indicator: lock icon if approval_required
  - Hover: shows "Edit" and "Disable" text links

Below main list — "Pending Review" section:
- Collapsible card with amber top border and warning icon
- Header: "2 skills pending review"
- Each pending item: name, domain badge, [Review] (navy link), [Approve] (green), [Reject] (red outline)

Skill Editor (full-page or large modal when editing):
- Left panel (40%): form fields
  - Name (text, monospace)
  - Domain (dropdown)
  - Triggers (tag input — type and press enter to add chips)
  - Approval Required (toggle switch)
  - Enabled (toggle switch)
- Right panel (60%): Markdown editor
  - Tab bar: "Edit" and "Preview" tabs
  - Edit: code editor textarea with line numbers, monospace font
  - Preview: rendered Markdown
- Bottom: "Save" (coral solid) and "Cancel" (gray outline)

AWS console resource-management style. Clean forms, clear actions.
```

---

## Prompt 9 — Reports & Backups Screen

```
Design a Reports & Backups screen for "LLMNetOps", light enterprise theme. Background #F5F7FA.

Two-panel layout:

Left panel (320px, white card):
- Section header: "Reports" with file count
- File list sorted by newest first. Each item:
  - File icon + filename (truncated if long)
  - Date below in small gray text: "May 10, 2026 09:23"
  - Size on right: "14.2 KB"
  - Selected item: light coral background tint #FFF5F2, coral left border
  - Hover: light gray background
  
- Divider line
  
- Section header: "Config Backups"
- Tree view grouped by router:
  - "▶ DTI" (expandable)
    - "DTI_20260510_103045.rsc — 128 KB"
    - "DTI_20260509_091200.rsc — 126 KB"
  - "▶ FIKES" (expandable)
    - ...
  - Checkboxes on backup files for comparison

Right panel (flex: 1, white card):
- Top bar: filename in bold, buttons on right: "Download" (navy outline), "Compare" (coral outline, only for backups)
- Content area:
  - For reports (.md files): Rendered Markdown with proper headings, tables, code blocks with copy button, and a floating TOC outline on the right margin
  - For backups (.rsc files): syntax-highlighted config with line numbers
  - For diff view: side-by-side diff — left panel (old) and right panel (new), green lines for additions, red for deletions, gray for unchanged

Feels like a document viewer in a cloud console. Clean typography, good line spacing.
```

---

## Prompt 10 — Metrics Screen

```
Design a Token Metrics screen for "LLMNetOps", light enterprise theme. Background #F5F7FA.

Section 1 — Summary Cards (top row, 4 cards):
- Card 1: "Total LLM Calls" — large number "1,247" with small trend indicator "+12% vs yesterday"
- Card 2: "Avg Context Usage" — percentage "34%" with circular progress indicator (coral fill)
- Card 3: "Avg Speed" — "18.3 tok/s" 
- Card 4: "Warnings" — "3" in amber with warning icon (or "0" in green with check)
Each card: white background, subtle border, small heading in gray uppercase, large value in navy.

Section 2 — "Per-Agent Breakdown" (white card):
- Data table with columns: Agent (alias + role), Total Calls, Avg CTX%, Avg PRED%, Avg TPS, Warnings
- Agent column shows alias in bold (EKO) with role in small gray (monitor) below
- Numeric columns right-aligned, monospace, tabular-nums
- Rows with warnings > 0 have subtle amber background tint
- Sort arrows on column headers
- Color-coded inline bars in CTX% and PRED% columns: green (<60%), amber (60-80%), red (>80%)

Section 3 — "Usage Trend" (white card):
- Toggle tabs: "24 Hours" / "7 Days" / "30 Days"
- Line chart area (placeholder):
  - X-axis: time periods
  - Y-axis: Context utilization %
  - One line per agent, using distinct colors
  - Legend at bottom showing agent aliases with color dots
- Below chart: "Exported from data/metrics.jsonl" in small gray

Enterprise analytics dashboard style. Clean charts, well-labeled axes.
```

---

## Prompt 11 — Settings Screen

```
Design a Settings screen for "LLMNetOps", light enterprise theme. Background #F5F7FA.

Tab navigation at top: horizontal tabs with bottom border indicator.
Tabs: Routers | Agents | Environment | NetBox | Memory
Active tab: navy text with coral bottom border. Inactive: gray text.

TAB 1 — Routers:
- White card with header "Router Configuration" and "Add Router" coral button on right
- Editable data table:
  - Columns: Name (text input), Host (text input), ROS Version (dropdown: 6 or 7), DHCP Servers (tag chips), Role
  - Each row has two action buttons: [Test] (navy outline, shows green ✓ or red ✗ after click) and [Remove] (red text link)
- Table has alternating row backgrounds
- Bottom: "Save Changes" coral solid button + "Discard" gray outline button

TAB 2 — Agents:
- Grid of cards (2 columns), one per agent:
  - Card header: Alias large bold (EKO) + agent name (monitor_agent) + toggle switch for enabled/disabled
  - Disabled agents have grayed-out card with "DISABLED" badge
  - Form fields within card: Model (text), num_ctx (number), num_predict (number), context_window (number), timeout (number)
  - Read-only sections: Tools (list of gray pills), Skills (list of coral pills)
  - Each card has subtle hover shadow
- Top right: "Reload Definitions" button (navy outline)

TAB 3 — Environment:
- White card with clean form layout:
  - Label above each field in gray uppercase
  - OLLAMA_BASE_URL: text input, current value shown, [Test Connection] button beside it showing result (green "Connected" or red "Failed")
  - OLLAMA_MODEL: dropdown (populated from Ollama API), showing current selection
  - Status row below: "Ollama server at localhost:11434 — 3 models available"
- "Save" coral button

TAB 4 — NetBox:
- One card per NetBox instance (kampus, idren):
  - Card header: instance name in bold + connection status badge
  - Fields: URL (text input), API Token (password input with eye toggle to show/hide)
  - [Test Connection] button per instance
- "Save" coral button

TAB 5 — Memory:
- White card: "Agent Memory — Router Facts"
- Filter: router dropdown selector
- Data table: Router (bold), Fact Type (badge), Value, Source, Updated At
- Select-all checkbox + "Clear Selected" red outline button
- Confirmation dialog before clearing

AWS console settings style — tabbed layout, clean forms, inline validation feedback.
```

---

## General Style Notes for All Prompts

Append to any prompt above for consistent styling:

```
Additional style requirements:
- This is a LIGHT theme — NOT dark mode. White cards on light gray #F5F7FA background.
- Sidebar is the only dark element: navy #1B3A5C background with white text.
- Font: IBM Plex Sans for all UI text. IBM Plex Mono for code, IPs, MACs, data values.
- Cards: white background, 1px border #E2E8F0, border-radius 8px, no heavy shadows.
- Primary action buttons: solid coral #E88B6A with white text, rounded 6px.
- Secondary buttons: white background with navy or gray border, navy text.
- Destructive buttons: white background with red border/text, or solid red.
- Status badges: small pill shapes with colored background tint + darker text (e.g., green-100 bg + green-800 text for "UP").
- Data tables: uppercase small gray headers, alternating white/#F8FAFC rows, right-aligned numbers.
- All numeric/code values in monospace with tabular-nums font variant.
- Links and interactive text: navy #1B3A5C, underline on hover.
- No rounded corners larger than 8px. No heavy shadows. No gradients.
- High information density — this is an operations tool, not a marketing site.
- Design language: AWS Console, Google Cloud Console, Datadog — premium enterprise SaaS.
```
