# Frontend Redesign — Design Document
**Date:** 2026-02-28
**Branch:** feature/frontend-mvp
**Status:** Approved

## Objective

Replace the current mobile-first blue-header chat layout with a clean, minimal interface matching the provided screenshot — similar in aesthetic to Claude/ChatGPT. Zero backend changes required.

## Target Layout

```
┌─────────────────────────────────────────────────────┐
│  PayTransparency          [Assistente] [Analisi Dati]│  fixed header, border-b
├─────────────────────────────────────────────────────┤
│                                                     │
│              Come posso aiutarti?                   │  empty state
│    Chiedi su normative, gap retributivi...          │  (hidden once msgs exist)
│                                                     │
│  [Cosa dice la Direttiva EU?] [Cos'è il pay gap?]  │  4 suggestion chips
│  [Obblighi di reporting]   [Sanzioni previste]      │
│                                                     │
│  ─ ─ ─ messages area (scrollabile) ─ ─ ─           │
│                                                     │
├─────────────────────────────────────────────────────┤
│  ( Scrivi un messaggio...                    [↑] )  │  pill input, fixed bottom
└─────────────────────────────────────────────────────┘
```

Tab "Analisi Dati":
```
├─────────────────────────────────────────────────────┤
│         📊 Carica i tuoi dati retributivi           │  empty state
│                                                     │
│     ┌─────────────────────────────────────────┐    │
│     │  ↑  Trascina CSV/Excel o clicca qui     │    │  drop zone
│     └─────────────────────────────────────────┘    │
│                                                     │
│  ─ ─ risultati analisi appaiono sotto ─ ─          │
└─────────────────────────────────────────────────────┘
```

## Approach

**Option A — Full template rewrite (chosen):** Rewrite `base.html` and `index.html`, add `marked.js` CDN, reuse all existing partials unchanged. Tab switching via pure JS (toggle CSS classes) — no server round-trip.

Rejected alternatives:
- Option B (separate `/analisi` route): unnecessary backend complexity
- Option C (HTMX tab swap): adds latency, no benefit for lightweight panels

## Components

| Component | Implementation |
|---|---|
| **Header** | `position: fixed`, `bg-white`, `border-b border-gray-100`, max-w centered, z-50 |
| **Tab pills** | Two `<button>` toggling active class. Active: `bg-white shadow-sm rounded-full`. Inactive: `text-gray-500 hover:text-gray-800` |
| **Empty state** | Hidden via JS when `#chat-messages` has children. Chips disappear after first send |
| **Suggestion chips** | `<button>` with `onclick` that sets input value + submits form. Disappear on first interaction |
| **Messages area** | `flex-1 overflow-y-auto`, padding-top for fixed header, padding-bottom for fixed input |
| **Input pill** | `fixed bottom-0`, `bg-white/80 backdrop-blur-sm`, subtle border, `rounded-full` |
| **Markdown rendering** | `marked.js` via CDN in `base.html`. `chat_message.html` renders assistant text through `marked.parse()` |
| **Upload drop zone (tab Analisi)** | Styled HTMX form with large clickable area, reuses existing `/api/upload` endpoint |

## Files Changed

Only templates — no backend modifications:

1. **`templates/base.html`**
   - Add `marked.js` CDN script
   - Remove `overflow-hidden` from body
   - Keep all existing HTMX event handlers (htmx:beforeSwap, htmx:responseError)
   - Add minimal custom CSS for scrollbar and backdrop-blur

2. **`templates/index.html`**
   - Full rewrite: header + 2 tab panels + empty states + suggestion chips + pill input
   - Tab "Assistente": chat interface with HTMX form
   - Tab "Analisi Dati": upload drop zone with HTMX form + results area
   - JS: tab switching, empty state toggle, chip click handler, auto-scroll

3. **`templates/partials/chat_message.html`**
   - Assistant bubble: replace `whitespace-pre-wrap` with `marked.parse()` rendering
   - User bubble: unchanged (plain text, no markdown needed)

**Unchanged:** `chat_error.html`, `upload_result.html`, `upload_error.html`

## Design Tokens

| Token | Value |
|---|---|
| Background | `#F7F7F8` (gray-50 equivalent) |
| Header bg | `#FFFFFF` |
| Tab active bg | `#FFFFFF` with `shadow-sm` |
| Tab inactive | `text-gray-500` |
| Input bg | `#FFFFFF` |
| Send button | `bg-blue-500` (indigo-blue, ~#6366F1 or #3B82F6) |
| User bubble | `bg-blue-500 text-white` |
| Assistant bubble | `bg-gray-100 text-gray-900` |
| Error bubble | `bg-amber-50 border-amber-200 text-amber-900` |
| Font | System stack: `-apple-system, BlinkMacSystemFont, "Segoe UI"...` |

## Constraints

- No new backend routes or Python changes
- No new npm/build step — CDN only (Tailwind CDN, HTMX CDN, marked.js CDN)
- All existing HTMX partial responses remain compatible (same `#chat-messages` target)
- Accessibility: ARIA roles preserved, min touch target 44px, sufficient color contrast
- Timeout handling (120s HTMX, 90s server) unchanged
