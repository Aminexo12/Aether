<!-- SEED — re-run /impeccable document once there's code to capture the actual tokens and components. -->

---
name: Aether
description: Personal AI agent for real-time aviation data analysis
colors:
  deep-space: "#0B1120"
  cockpit-surface: "#141D2F"
  instrument-panel: "#1A2540"
  contrail: "#1E2D47"
  sky-blue: "#38BDF8"
  horizon-amber: "#F59E0B"
  high-altitude: "#E2E8F0"
  cloud: "#8899AA"
  fog: "#4A5E78"
typography:
  display:
    fontFamily: "Space Grotesk, system-ui, sans-serif"
    fontSize: "clamp(1.75rem, 3vw, 2.25rem)"
    fontWeight: 300
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Space Grotesk, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.3
  title:
    fontFamily: "Space Grotesk, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Space Grotesk, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.1em"
  mono:
    fontFamily: "JetBrains Mono, Menlo, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  none: "0px"
  sm: "2px"
  md: "4px"
  lg: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  xxl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.sky-blue}"
    textColor: "{colors.deep-space}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "#62CCFA"
    textColor: "{colors.deep-space}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.sky-blue}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  input-default:
    backgroundColor: "{colors.cockpit-surface}"
    textColor: "{colors.high-altitude}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  input-focus:
    backgroundColor: "{colors.cockpit-surface}"
    textColor: "{colors.high-altitude}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  chat-user:
    backgroundColor: "{colors.instrument-panel}"
    textColor: "{colors.high-altitude}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  chat-assistant:
    backgroundColor: "{colors.deep-space}"
    textColor: "{colors.high-altitude}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
---

# Design System: Aether

## 1. Overview

**Creative North Star: "The High Altitude Instrument"**

Aether's interface takes its language from precision instruments — altimeters, radar screens, navigation displays — not as skeuomorphic recreation but as a philosophy: every element exists to convey information, nothing exists to look impressive. The surface is deep space, the data glows against it, and the operator (the viewer) reads it in a single focused pass.

The palette is committed. Deep navy owns 70%+ of every screen. Sky blue appears only where it earns it: interactive elements, live data, the cursor of attention. Horizon amber is reserved for anomalies and warnings — its rarity is its entire meaning. When something turns amber, it matters.

Motion is aircraft-inspired: smooth, directional, deliberate. Nothing bounces. Nothing spins. Transitions happen along the axis of intent — a panel slides in from the direction it represents, a message arrives from below as if ascending from the input field, data updates with a brief fade not a flash. The base state is always still.

**Key Characteristics:**
- Dark as primary, non-negotiable — instruments are read in low light
- Sharp geometry (4px max radius) — precision tools do not have soft corners
- Two-font system: Space Grotesk for UI, JetBrains Mono for data
- Two accents only: sky blue for interaction, horizon amber for anomaly
- Dense by default — whitespace is used for rhythm, not emptiness

## 2. Colors: The Altitude Palette

Five layers of depth through tonal stepping, not shadows. Two accents with fixed roles and no exceptions.

### Primary
- **Sky Blue** (`#38BDF8`, oklch(76% 0.12 218)): The single interactive accent. Used on primary buttons, active navigation states, focus rings, live-data labels, hyperlinks, and the chat cursor. Appears on ≤20% of any given screen.

### Secondary
- **Horizon Amber** (`#F59E0B`, oklch(78% 0.14 75)): Anomaly and warning signal exclusively. Used on anomaly detection badges, alert states, and warning text. Never used decoratively. If something is amber, the user must pay attention.

### Neutral
- **Deep Space** (`#0B1120`, oklch(8% 0.02 248)): Primary background. The canvas.
- **Cockpit Surface** (`#141D2F`, oklch(12% 0.025 245)): Secondary background. Sidebars, header, input areas.
- **Instrument Panel** (`#1A2540`, oklch(16% 0.03 243)): Elevated surfaces. Hover states, selected rows, message containers.
- **Contrail** (`#1E2D47`, oklch(20% 0.03 242)): Borders and dividers. Structural lines only — never decorative.
- **High Altitude** (`#E2E8F0`, oklch(92% 0.008 240)): Primary text. All readable body copy.
- **Cloud** (`#8899AA`, oklch(62% 0.018 240)): Secondary text. Labels, metadata, captions.
- **Fog** (`#4A5E78`, oklch(40% 0.025 240)): Disabled text, placeholder copy.

**The Two-Accent Rule.** Sky blue and horizon amber are the only colors that break from the neutral scale. No purple, no green, no teal, no gradient fills. Adding a third accent is prohibited.

**The Amber Reservation Rule.** Horizon amber appears only in response to system-detected anomalies or critical warnings. Using it for decorative highlights, section titles, or emphasis text is forbidden — it destroys the signal.

## 3. Typography: Instrument + Data

**UI Font:** Space Grotesk (with system-ui, sans-serif fallback)
**Data/Code Font:** JetBrains Mono (with Menlo, monospace fallback)
**Body/Prose Font:** Inter (with system-ui fallback — chat responses, long-form content only)

**Character:** Space Grotesk has an engineered quality — slightly mechanical letterforms, confident spacing — that reads as designed rather than default. JetBrains Mono is the natural pairing for ICAO codes, callsigns, coordinates, and latency numbers. They do not compete because they inhabit separate domains: UI chrome vs. data.

### Hierarchy
- **Display** (300 weight, clamp(1.75rem, 3vw, 2.25rem), -0.02em tracking, 1.15 leading): Page titles, the Aether wordmark. Rarely used.
- **Headline** (500 weight, 1.25rem, 1.3 leading): Section headers, panel titles, key metrics.
- **Title** (500 weight, 1rem, 1.4 leading): Card headers, navigation items, subsection labels.
- **Body** (400 weight Inter, 0.875rem, 1.65 leading, max 65ch): Chat responses, RAG-retrieved content, descriptive copy.
- **Label** (600 weight Space Grotesk, 0.6875rem, uppercase, 0.1em tracking, 1.0 leading): UI chrome labels, button text, status badges, column headers. Always uppercase.
- **Mono** (400 weight JetBrains Mono, 0.8125rem, 1.5 leading): ICAO24 codes, callsigns, coordinates, altitude/speed values, timestamps, API response snippets.

**The Mono Data Rule.** Every piece of raw aviation data — callsign, ICAO code, latitude/longitude, altitude in meters, velocity in m/s — is rendered in JetBrains Mono, not Inter or Space Grotesk. The type itself signals "this is a measurement, not a description."

**The No-Sentence-Case Label Rule.** Labels and badges are uppercase Space Grotesk. Never title case, never sentence case for UI chrome. The visual weight of uppercase with 0.1em tracking earns attention without size.

## 4. Elevation

This system uses **tonal layering**, not shadows. Depth is expressed through the neutral color steps: Deep Space → Cockpit Surface → Instrument Panel → Contrail. These four steps are the full elevation vocabulary.

Shadows are absent from the default state. They appear only as a functional response to hover or active drag — a faint `0 4px 20px rgba(0,0,0,0.4)` that reads as slight lift, never as a design feature.

**The Flat-by-Default Rule.** No element casts a shadow at rest. Hover on an interactive card may add a single diffuse shadow (`0 4px 20px rgba(0, 0, 0, 0.4)`) to communicate liftability. Modals add `0 24px 48px rgba(0, 0, 0, 0.6)`. Nothing else.

**The Tonal Ladder Rule.** Depth increases one step at a time. A panel on Deep Space uses Cockpit Surface. A selected row in a Cockpit Surface list uses Instrument Panel. Skipping steps (Deep Space directly to Instrument Panel) is only permitted for modals or drawers that intentionally float above all other content.

## 5. Components

### Buttons
Sharp-edged, uppercase, confident. Buttons read as controls, not affordances.
- **Shape:** 4px radius — gently squared, never pill-shaped
- **Primary:** Sky blue background (`#38BDF8`), Deep Space text (`#0B1120`), Space Grotesk 600 uppercase label, 10px/20px padding. On hover: background shifts to `#62CCFA`, transform: translateY(-1px) over 150ms ease-out-quart.
- **Ghost:** Transparent background, 1px Contrail border at rest → 1px Sky Blue border on hover, Sky Blue text. Used for secondary actions.
- **Disabled:** Fog text (`#4A5E78`), Cockpit Surface background, 1px Contrail border. No hover effect.
- **Focus visible:** 2px Sky Blue outline, 2px offset. No glow, no blur.

### Inputs / Chat Field
- **Style:** Cockpit Surface background, 1px Contrail border, 4px radius, 10px/14px padding, Body font
- **Focus:** Border transitions from Contrail (`#1E2D47`) to Sky Blue (`#38BDF8`) over 150ms. No glow.
- **Placeholder:** Fog color (`#4A5E78`), never italic
- **Error:** Border shifts to Horizon Amber. Never red.
- **Send button:** Embedded in the field at the right edge, icon-only, Sky Blue at rest, 20% brighter on hover

### Chat Messages
These are the anti-ChatGPT. No alternating bubble layout. No left/right asymmetry. Full-width blocks, stacked vertically, differentiated only by label and surface.
- **User message:** Instrument Panel background (`#1A2540`), full width, Label "YOU" in Cloud mono above the content, 4px radius, 16px padding
- **Assistant message:** Deep Space background (same as canvas), distinguished by a 2px Sky Blue left border (the only permitted side border in this system — it is structural, not decorative) and Label "AETHER" in Sky Blue mono above content. 16px padding.
- **Tool call indicator:** Between messages when agent calls a tool — monospace label in Cloud color: `› calling get_live_flights...` — no animation, no spinner, pure text

### Navigation Tabs
Three tabs: Chat, Map, Analytics.
- **Active:** Full brightness High Altitude text, 2px Sky Blue underline border-bottom, no background
- **Inactive:** Cloud text (`#8899AA`), no border, no background
- **Hover:** High Altitude text, no border
- **No pill backgrounds, no rounded selection states**

### Data Badges / Status Chips
- **Default:** Instrument Panel background, Cloud text, Label font uppercase, 2px radius, 4px/8px padding
- **Live:** Sky Blue text on Instrument Panel background. Not a filled chip.
- **Anomaly:** Horizon Amber text on Instrument Panel background. Same structure.
- **Never use filled colored chips** — color belongs to the text, not the container

### Flight Data Row (Signature Component)
The core list item in the live flights view.
- Background: Cockpit Surface at rest, Instrument Panel on hover
- ICAO24 and callsign in JetBrains Mono, Sky Blue
- Country, altitude, velocity in Cloud color mono
- On-ground flag: Fog color label text "ON GROUND", amber when anomaly detected
- Transition: 120ms background color change on hover, no scale transform

## 6. Do's and Don'ts

### Do:
- **Do** render all aviation data values (ICAO codes, callsigns, altitudes, coordinates, velocities, timestamps) in JetBrains Mono.
- **Do** keep button and badge text uppercase with 0.1em tracking.
- **Do** use only Contrail borders (1px `#1E2D47`) for structural separation — never colored borders except the assistant message's sky-blue left accent.
- **Do** treat Horizon Amber as a reserved signal: anomalies and critical warnings only.
- **Do** step through the tonal ladder one level at a time (Deep Space → Cockpit Surface → Instrument Panel).
- **Do** use `prefers-reduced-motion` to replace translational animations with instant fades.
- **Do** test legibility for deuteranopia: amber and blue must communicate meaning independently of color (use labels alongside).
- **Do** load Space Grotesk and JetBrains Mono from Google Fonts via custom CSS injection.

### Don't:
- **Don't** use white (`#ffffff`) or pure black (`#000000`) anywhere. Tint every neutral toward the brand hue.
- **Don't** add a third accent color. Two is the limit and both roles are assigned.
- **Don't** use gradient text (`background-clip: text`). Emphasis through weight or color, never gradient fills on copy.
- **Don't** build a generic AI product look — white background, rounded cards, gradient hero sections, "powered by" badges.
- **Don't** recreate the ChatGPT/Claude UI — no alternating left/right message bubbles, no gray background chat containers.
- **Don't** use neon cyberpunk aesthetics — no glowing borders, no animated grid lines, no excessive visual noise.
- **Don't** use the Notion/Linear off-white cream look — SaaS startup cream is the opposite of this system.
- **Don't** use corner radius larger than 8px anywhere. Pilot instruments have beveled edges, not rounded corners.
- **Don't** use shadows at rest. The flat-by-default rule is absolute.
- **Don't** use border-left colored stripes decoratively — the assistant message's sky-blue left border is the sole exception and it is structural.
- **Don't** use the hero-metric template — big number, small label, gradient accent — for any data display.
- **Don't** display identical card grids. Vary information density and layout across sections.
