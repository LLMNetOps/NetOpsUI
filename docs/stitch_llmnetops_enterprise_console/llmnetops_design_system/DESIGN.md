---
name: LLMNetOps Design System
colors:
  surface: '#f7f9fc'
  surface-dim: '#d8dadd'
  surface-bright: '#f7f9fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f7'
  surface-container: '#eceef1'
  surface-container-high: '#e6e8eb'
  surface-container-highest: '#e0e3e6'
  on-surface: '#191c1e'
  on-surface-variant: '#43474e'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f4'
  outline: '#73777f'
  outline-variant: '#c3c6cf'
  surface-tint: '#436084'
  primary: '#002444'
  on-primary: '#ffffff'
  primary-container: '#1b3a5c'
  on-primary-container: '#87a4cc'
  inverse-primary: '#abc9f2'
  secondary: '#94492d'
  on-secondary: '#ffffff'
  secondary-container: '#fe9d7b'
  on-secondary-container: '#773218'
  tertiary: '#142438'
  on-tertiary: '#ffffff'
  tertiary-container: '#2a3a4e'
  on-tertiary-container: '#93a4bc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4ff'
  primary-fixed-dim: '#abc9f2'
  on-primary-fixed: '#001c38'
  on-primary-fixed-variant: '#2b486b'
  secondary-fixed: '#ffdbcf'
  secondary-fixed-dim: '#ffb59c'
  on-secondary-fixed: '#380c00'
  on-secondary-fixed-variant: '#773218'
  tertiary-fixed: '#d3e4fe'
  tertiary-fixed-dim: '#b7c8e1'
  on-tertiary-fixed: '#0b1c30'
  on-tertiary-fixed-variant: '#38485d'
  background: '#f7f9fc'
  on-background: '#191c1e'
  surface-variant: '#e0e3e6'
typography:
  display-lg:
    fontFamily: IBM Plex Sans
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: IBM Plex Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-sm:
    fontFamily: IBM Plex Sans
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: IBM Plex Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: IBM Plex Sans
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: IBM Plex Mono
    fontSize: 13px
    fontWeight: '450'
    lineHeight: 18px
  data-mono-sm:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: '450'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  sidebar_width: 240px
  header_height: 56px
  container_gutter: 24px
  component_padding_x: 12px
  component_padding_y: 8px
  stack_gap_sm: 4px
  stack_gap_md: 12px
  stack_gap_lg: 24px
---

## Brand & Style
The design system is engineered for high-stakes enterprise network management, where clarity and rapid data synthesis are paramount. The personality is **authoritative, precise, and utilitarian**, stripping away decorative elements to focus on operational efficiency. 

The aesthetic follows a **Modern Corporate** approach with a focus on high information density. It prioritizes clarity over visual flourish, utilizing a structured layout that mirrors the complexity of AI-driven network operations. The interface evokes a sense of "command and control," providing administrators with a stable, predictable environment to manage campus infrastructure. 

Key principles include:
- **Efficiency over Embellishment:** Every pixel must serve a functional purpose.
- **Data Density:** Layouts are optimized to display large volumes of logs, metrics, and agent states without overwhelming the user.
- **Visual Stability:** A rigid grid and consistent alignment create a reliable workspace for long-term monitoring.

## Colors
The palette is built for professional utility, using a "Navy and Coral" foundation to distinguish between structural elements and actionable triggers.

- **Primary (Navy - #1B3A5C):** Reserved for high-level navigation, sidebars, and brand-critical indicators. It provides a grounded, stable frame for the application.
- **Accent (Coral/Salmon - #E88B6A):** Used sparingly but decisively for primary calls to action, active AI agent status, and critical brand highlights.
- **Backgrounds:** The global page background uses a "Cool Gray" (#F5F7FA) to reduce eye strain, while interactive surfaces and cards utilize pure White (#FFFFFF).
- **Semantic Colors:** Success, Warning, and Error states follow industry standards but are softened through the use of high-contrast text on desaturated background tints for better legibility in dense tables.

## Typography
This design system employs a dual-typeface strategy to separate narrative UI from technical data.

- **IBM Plex Sans:** Used for all interface instructions, labels, and headings. It provides a modern, neutral tone that remains legible at small sizes.
- **IBM Plex Mono:** Used strictly for technical values including IP addresses, MAC addresses, CLI output, and numeric metrics. This ensures that characters like '0' and 'O' are never confused during critical network troubleshooting.
- **Hierarchy:** We use a tight scale. Most UI text sits at 13px or 14px to maximize information density. Table headers use a bold, uppercase 11px style to provide clear categorization without occupying excessive vertical space.

## Layout & Spacing
The layout is based on a **Fixed-Fluid hybrid model** designed for professional desktop displays.

- **Sidebar:** A fixed 240px navigation rail on the left, using the Navy primary color. It features a 3px vertical "Accent" indicator for the active route.
- **Header:** A fixed 56px white bar with a 1px #E2E8F0 bottom border, housing global search and agent status notifications.
- **Grid:** Content is housed within a fluid container with 24px margins. For complex dashboards, a 12-column grid is used, but for data-heavy views, simple flexbox stacks are preferred to maintain density.
- **Density:** We use a "Compact" spacing rhythm. Vertical padding in lists and tables is kept to 8px to ensure more data is visible above the fold.

## Elevation & Depth
This design system avoids heavy shadows and skeuomorphism in favor of **Tonal Layering and Borders**.

- **Level 0 (Background):** #F5F7FA (Cool Gray). Used for the canvas.
- **Level 1 (Surface):** #FFFFFF (White). All cards, tables, and modals sit on this level.
- **Borders:** Depth is primarily communicated through 1px solid borders (#E2E8F0). This creates a "blueprint" feel that is clean and structured.
- **Shadows:** Only used for floating elements like dropdown menus or modals. When used, shadows are highly diffused and low-opacity: `0px 4px 12px rgba(0, 0, 0, 0.05)`.

## Shapes
The shape language is controlled and professional. Elements use a **Standard Rounded (0.5rem)** corner radius for cards and containers to prevent the UI from feeling overly aggressive or "brutalist," while maintaining a modern enterprise look.

- **Buttons & Inputs:** 4px to 8px radius (rounded-md).
- **Cards:** 8px radius (rounded-lg).
- **Badges/Pills:** Fully rounded (pill-shaped) to distinguish them from interactive buttons.

## Components
### Buttons
- **Primary:** Solid #E88B6A background with white text. High visibility for core actions like "Deploy Agent" or "Save Changes."
- **Secondary:** White background with #1B3A5C border and text. Used for "Cancel" or "Export."
- **Ghost:** No background/border, Navy text. Used for low-priority actions in table rows.

### Tables
- **Structure:** 1px #E2E8F0 border, no horizontal lines between rows is preferred if zebra-striping is used.
- **Zebra Striping:** Even rows use #F8FAFC; odd rows use #FFFFFF.
- **Headers:** 11px uppercase, bold, #64748B text color.
- **Data:** Right-align all numeric and monospace data.

### Cards
- White background, 1px #E2E8F0 border, 8px radius.
- Padding should be a consistent 16px or 24px.
- Use a 1px bottom border for card titles to separate header information from content.

### Badges / Status Indicators
- **Success:** #DCFCE7 background, #166534 text.
- **Warning:** #FEF3C7 background, #92400E text.
- **Error:** #FEE2E2 background, #991B1B text.
- **Style:** Small pill-shaped containers with 'IBM Plex Sans' Bold 11px text.

### Input Fields
- 1px #E2E8F0 border, 4px corner radius.
- Active state uses a 1px #1B3A5C border and a subtle Navy glow (2px).
- Labels always sit above the input field in 12px Medium weight.

### Sidebar Nav Items
- Default: #FFFFFF (60% opacity) text on #1B3A5C.
- Active: #FFFFFF text with a 3px #E88B6A left-border highlight and a subtle 10% white overlay background.