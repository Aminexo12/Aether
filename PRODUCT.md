# Product

## Register

product

## Users

Amine, a developer who loves traveling and aviation, built this for himself and shares it as a portfolio piece. The viewer opens the app once, forms a judgment in the first few seconds, and will probe it with real questions. They are likely technical — developers, data people — and will notice if something feels fake or generic. The primary emotional context is curiosity: someone who finds flight data genuinely fascinating.

## Product Purpose

Aether is a personal AI agent for real-time aviation data analysis. It combines a chat interface (LangGraph + Claude), a live flight map (pydeck), and an analytics dashboard (Plotly) into a single tool that answers questions about global air traffic, EU flight regulations, and flight anomalies. It exists because the builder is passionate about travel and wanted to understand what is happening in the sky at any given moment. Success means someone opens it, asks a real question about a flight or a regulation, gets a precise answer, and feels the same curiosity the builder felt when making it.

## Brand Personality

Precise, calm, expert. The interface should feel like a well-designed instrument panel — confident, uncluttered, everything in its place. Not cold or austere, but quietly authoritative. The aviation subject matter should be felt in the aesthetic without being literal (no clip-art planes, no airline logos).

## Anti-references

- Generic AI product look: white background, rounded cards, gradient hero, gradient text, "powered by GPT" vibes.
- ChatGPT / Claude UI clones: message bubbles on alternating sides, gray background, no visual identity.
- Neon cyberpunk dashboards: glowing borders, animated grids, excessive data noise.
- SaaS startup cream: Notion-style off-white with gray accents and Inter at 400 weight everywhere.
- Anything that looks assembled from a component kit without thought.

## Design Principles

1. **Instrument, not decoration.** Every visual element earns its place by conveying data or guiding action. Ornamentation is waste.
2. **The subject shapes the aesthetic.** Sky, altitude, and flight are not metaphors to illustrate — they are the color palette, the motion language, the spatial logic.
3. **Expert confidence over approachability theater.** Dense information done well is more impressive than simplified interfaces that explain themselves. Trust the viewer to be smart.
4. **One focal point per screen.** The map, the chat, the charts — each view has a dominant element. Supporting elements recede.
5. **Stillness with purpose.** Calm base state. Motion only when data changes or the user acts — and when it moves, it moves like an aircraft on approach: smooth, directional, unhurried.

## Accessibility & Inclusion

WCAG AA baseline. Dark theme is primary (aviation data is read on screens in low-light conditions). Motion references aircraft movement — smooth, translational, unhurried. Respect `prefers-reduced-motion` by substituting fades for translational animations. Color choices should remain legible for deuteranopia (avoid green/red as sole signal carriers for flight status).
