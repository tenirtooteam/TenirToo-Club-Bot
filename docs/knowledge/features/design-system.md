---
type: feature-detail
title: Design System (Premium Minimalist)
description: Visual design tokens for the Telegram Mini App — palette, typography, glassmorphism, iconography.
source_anchor: CP-4
timestamp: 2026-07-02
tags: [design, ui, webapp, tma]
---

# Design System (Premium Minimalist)

> Moved from `CONTEXT_PROMPT.md` [CP-4] during the two-tier documentation migration.
> These are descriptive visual tokens (reference data), consulted on demand when
> touching the WebApp frontend — not a coding rule.

## [CP-4.1] Core Palette
- **Background**: `#050505` (Deep Black).
- **Cards/Containers**: `rgba(20, 20, 20, 0.7)` (Glass Dark).
- **Borders**: `rgba(255, 255, 255, 0.08)` (Subtle White).
- **Accents**: Pure White (`#ffffff`) for primary, Dim White (`rgba(255, 255, 255, 0.6)`) for secondary.

## [CP-4.2] Typography
- **Font Family**: `Outfit` (Google Fonts).
- **Headings**: Bold, tight tracking (`letter-spacing: -1px`), line-height 1.1.

## [CP-4.3] Glassmorphism & Interactivity
- **Blur Effect**: `backdrop-filter: blur(20px)`.
- **Corner Radii**: Standard `20px` or `24px`.
- **Micro-Animations**: Scale down on active state (`0.96`), slight opacity transitions.

## [CP-4.4] Iconography & Layout
- **System Emojis**: 🏔 (Expedition), 📍 (Topic), 👤 (Profile), 🛡️ (Admin), 🔎 (Search).
- **Grid Layout**: Use 2-column grids for menus to maximize screen efficiency on mobile.
