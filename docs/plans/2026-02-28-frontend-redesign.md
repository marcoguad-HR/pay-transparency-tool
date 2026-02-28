# Frontend Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the blue-header mobile chat layout with a clean, minimal ChatGPT/Claude-style interface matching the provided screenshot — with tab navigation, suggestion chips, pill input, and markdown rendering.

**Architecture:** Single-page Jinja2 template rewrite. Tab switching via pure client-side JS (toggle `hidden` class). Two independent message areas (`#chat-messages` for the Assistente tab, `#analysis-messages` for the Analisi Dati tab). All existing HTMX partial responses stay compatible — only target IDs stay the same. Backend: zero changes.

**Tech Stack:** Jinja2 + Tailwind CDN + HTMX 2.0.4 + marked.js 9 (CDN)

---

## Task 1: Update `base.html` — add marked.js, fix CSS

**Files:**
- Modify: `templates/base.html`

**Step 1: Read the current file**

Already read in context. Current issues to fix:
- Body has no `overflow-hidden` (remove it — the new layout needs natural scroll per panel)
- Need `marked.js` CDN added before `</head>`
- Need markdown CSS rules for `.markdown-body`
- The `htmx:responseError` handler needs to detect the active tab's messages area

**Step 2: Write the new `base.html`**

Replace `templates/base.html` with:

```html
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#ffffff">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <title>Pay Transparency Tool</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>

    <!-- marked.js — markdown rendering for assistant responses -->
    <script src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"></script>
    <script>
        marked.setOptions({ breaks: true, gfm: true });
    </script>

    <script>
        document.addEventListener('htmx:beforeSwap', function(evt) {
            if (evt.detail.xhr.status >= 400) {
                evt.detail.shouldSwap = true;
                evt.detail.isError = false;
            }
        });

        document.addEventListener('htmx:responseError', function(evt) {
            // Inject error bubble into whichever messages area is currently active
            var chatPanel = document.getElementById('panel-assistente');
            var isChat = chatPanel && !chatPanel.classList.contains('hidden');
            var targetId = isChat ? 'chat-messages' : 'analysis-messages';
            var target = document.getElementById(targetId);
            if (!target) return;

            var status = evt.detail.xhr ? evt.detail.xhr.status : -1;
            var msg = (status === 0)
                ? 'La richiesta ha impiegato troppo tempo o si è verificato un errore di rete. Riprova.'
                : 'Errore imprevisto (codice ' + status + '). Riprova tra qualche istante.';

            var errorHtml =
                '<div class="flex justify-start">' +
                '<div class="max-w-[85%] md:max-w-2xl bg-amber-50 text-amber-900 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-amber-200">' +
                '<div class="flex items-start gap-2">' +
                '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>' +
                '<line x1="12" y1="9" x2="12" y2="13"></line>' +
                '<line x1="12" y1="17" x2="12.01" y2="17"></line>' +
                '</svg>' +
                '<div class="flex-1"><p class="text-sm">' + msg + '</p></div>' +
                '</div></div></div>';

            target.insertAdjacentHTML('beforeend', errorHtml);
            target.scrollTop = target.scrollHeight;
            if (isChat) { if (typeof updateChatEmptyState === 'function') updateChatEmptyState(); }
            else { if (typeof updateAnalysisEmptyState === 'function') updateAnalysisEmptyState(); }
        });
    </script>

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
        }

        /* HTMX loading indicator */
        .htmx-indicator { display: none; }
        .htmx-request .htmx-indicator,
        .htmx-request.htmx-indicator { display: flex; }

        /* Markdown rendered content inside assistant bubbles */
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {
            font-weight: 600;
            margin-top: 0.6rem;
            margin-bottom: 0.2rem;
        }
        .markdown-body h3 { font-size: 0.875rem; }
        .markdown-body ul, .markdown-body ol {
            padding-left: 1.25rem;
            margin-top: 0.2rem;
            margin-bottom: 0.2rem;
        }
        .markdown-body li { margin-bottom: 0.1rem; }
        .markdown-body p { margin-bottom: 0.25rem; }
        .markdown-body p:last-child { margin-bottom: 0; }
        .markdown-body strong { font-weight: 600; }
        .markdown-body code {
            background: rgba(0,0,0,0.07);
            padding: 0.1em 0.3em;
            border-radius: 3px;
            font-size: 0.82em;
            font-family: "SF Mono", "Fira Code", monospace;
        }
        .markdown-body pre {
            background: rgba(0,0,0,0.07);
            padding: 0.75rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 0.4rem 0;
        }
        .markdown-body pre code { background: none; padding: 0; }
    </style>
</head>
<body class="bg-gray-50 h-screen">
    {% block content %}{% endblock %}
</body>
</html>
```

**Step 3: Verify the file saved correctly**

```bash
head -5 templates/base.html
# Expected: <!DOCTYPE html>
```

**Step 4: Commit**

```bash
git add templates/base.html
git commit -m "feat: update base.html — add marked.js, markdown CSS, smart error handler"
```

---

## Task 2: Update `chat_message.html` — add markdown rendering

**Files:**
- Modify: `templates/partials/chat_message.html`

**Context:** The assistant bubble currently uses `whitespace-pre-wrap` with raw text. We need to render the text as markdown using `marked.parse()`. The technique uses `document.currentScript.previousElementSibling` to reference the exact element just rendered — reliable even when multiple messages arrive quickly.

The user bubble stays plain text (users don't write markdown).

**Step 1: Write the new partial**

Replace `templates/partials/chat_message.html` with:

```html
{% if role == "user" %}
<!-- Bolla utente — destra, sfondo blu -->
<div class="flex justify-end">
    <div class="max-w-[85%] md:max-w-2xl bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
        <p class="text-sm whitespace-pre-wrap leading-relaxed">{{ text }}</p>
        <p class="text-xs text-blue-200 mt-1 text-right">{{ timestamp }}</p>
    </div>
</div>
{% else %}
<!-- Bolla assistente — sinistra, sfondo grigio, testo markdown -->
<div class="flex justify-start">
    <div class="max-w-[85%] md:max-w-2xl bg-white text-gray-900 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100">
        <div class="markdown-body text-sm leading-relaxed"></div>
        <script>
            (function() {
                var bubble = document.currentScript.previousElementSibling;
                bubble.innerHTML = marked.parse({{ text | tojson }});
            })();
        </script>
        <p class="text-xs text-gray-400 mt-2 text-right">{{ timestamp }}</p>
    </div>
</div>
{% endif %}
```

**Step 2: Verify**

```bash
cat templates/partials/chat_message.html
# Expected: both user and assistant bubbles present, script tag present
```

**Step 3: Commit**

```bash
git add templates/partials/chat_message.html
git commit -m "feat: add markdown rendering for assistant bubbles via marked.js"
```

---

## Task 3: Rewrite `index.html` — skeleton, header, tab navigation

**Files:**
- Modify: `templates/index.html`

**Context:** Full rewrite. Build it in layers. This task: outer skeleton + fixed header + tab buttons + JS tab-switch function.

**Step 1: Write the skeleton + header**

Replace `templates/index.html` with the following. Read carefully — the structure is:

```
body
  fixed header (logo + tab pills)
  .h-screen.flex.flex-col (fills viewport)
    .flex-1.relative.overflow-hidden.pt-14 (panels container)
      #panel-assistente  (absolute inset-0, flex-col — default visible)
      #panel-analisi     (absolute inset-0, flex-col — hidden)
    #thinking            (fixed, near bottom, htmx-indicator)
    #footer-assistente   (fixed bottom, pill chat input — default visible)
    #footer-analisi      (fixed bottom, upload button — hidden)
```

```html
{% extends "base.html" %}

{% block content %}

<!-- ================================================================
     FIXED HEADER
     ================================================================ -->
<header class="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-100">
    <div class="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">

        <!-- Logo -->
        <span class="font-semibold text-gray-900 tracking-tight text-[15px]">PayTransparency</span>

        <!-- Tab navigation pills -->
        <nav class="flex items-center bg-gray-100 rounded-full p-1 gap-0.5" role="tablist" aria-label="Sezioni">
            <button id="tab-assistente"
                    role="tab"
                    aria-selected="true"
                    aria-controls="panel-assistente"
                    onclick="switchTab('assistente')"
                    class="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-medium transition-all duration-150 bg-white shadow-sm text-gray-900">
                <!-- Chat bubble icon -->
                <svg class="w-[15px] h-[15px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                Assistente
            </button>
            <button id="tab-analisi"
                    role="tab"
                    aria-selected="false"
                    aria-controls="panel-analisi"
                    onclick="switchTab('analisi')"
                    class="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-medium transition-all duration-150 text-gray-500 hover:text-gray-700">
                <!-- Bar chart icon -->
                <svg class="w-[15px] h-[15px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                Analisi Dati
            </button>
        </nav>

    </div>
</header>

<!-- ================================================================
     PANELS CONTAINER (fills screen below header)
     ================================================================ -->
<div class="h-screen flex flex-col">
    <div class="flex-1 relative overflow-hidden pt-14">

        <!-- PLACEHOLDER: panels go here (Tasks 4 and 5) -->

    </div>

    <!-- PLACEHOLDER: thinking indicator (Task 6) -->
    <!-- PLACEHOLDER: footers (Task 6) -->
</div>

<!-- ================================================================
     JAVASCRIPT
     ================================================================ -->
<script>
    function switchTab(tab) {
        var tabs = ['assistente', 'analisi'];
        tabs.forEach(function(t) {
            var panel   = document.getElementById('panel-' + t);
            var btn     = document.getElementById('tab-' + t);
            var footer  = document.getElementById('footer-' + t);
            var isActive = (t === tab);

            // Panel
            if (panel)  panel.classList.toggle('hidden', !isActive);
            // Footer
            if (footer) footer.classList.toggle('hidden', !isActive);
            // Tab button
            if (btn) {
                btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
                if (isActive) {
                    btn.classList.add('bg-white', 'shadow-sm', 'text-gray-900');
                    btn.classList.remove('text-gray-500', 'hover:text-gray-700');
                } else {
                    btn.classList.remove('bg-white', 'shadow-sm', 'text-gray-900');
                    btn.classList.add('text-gray-500', 'hover:text-gray-700');
                }
            }
        });
    }
</script>

{% endblock %}
```

**Step 2: Start the server and verify the header renders**

```bash
uvicorn app:app --reload --port 8000
# Then open http://localhost:8000 in browser
# Expected: white header with "PayTransparency" logo + two tab buttons visible
# Clicking tabs should not crash (panels don't exist yet but no JS error)
```

**Step 3: Commit**

```bash
git add templates/index.html
git commit -m "feat: index.html skeleton — fixed header + tab navigation + switchTab()"
```

---

## Task 4: Add Tab Assistente panel — empty state, chips, messages area

**Files:**
- Modify: `templates/index.html`

**Context:** Replace the `<!-- PLACEHOLDER: panels go here -->` comment with the full Assistente panel. The panel uses `absolute inset-0` so it fills the panels container. The empty state (`#chat-empty-state`) is a separate `absolute inset-0` layer with `pointer-events-none` on the container (chips have `pointer-events-auto`).

**Step 1: Insert the Assistente panel**

In `index.html`, replace:
```html
        <!-- PLACEHOLDER: panels go here (Tasks 4 and 5) -->
```

With:

```html
        <!-- ============================================================
             PANEL: ASSISTENTE
             ============================================================ -->
        <div id="panel-assistente"
             role="tabpanel"
             aria-labelledby="tab-assistente"
             class="absolute inset-0 flex flex-col">

            <!-- Messages area -->
            <main id="chat-messages"
                  class="flex-1 overflow-y-auto px-4 py-6 pb-28 max-w-3xl mx-auto w-full space-y-4"
                  role="log"
                  aria-live="polite"
                  aria-atomic="false">
            </main>

            <!-- Empty state — overlay, disappears when messages exist -->
            <div id="chat-empty-state"
                 class="absolute inset-0 flex flex-col items-center justify-center pb-24 pointer-events-none"
                 aria-hidden="true">

                <h1 class="text-[1.75rem] font-semibold text-gray-900 mb-2 text-center px-4">
                    Come posso aiutarti?
                </h1>
                <p class="text-gray-500 text-center text-sm px-4 mb-8">
                    Chiedi informazioni su normative, gap retributivi e<br class="hidden sm:inline"> trasparenza salariale.
                </p>

                <!-- Suggestion chips -->
                <div id="chat-chips"
                     class="flex flex-wrap gap-2 justify-center max-w-lg px-4 pointer-events-auto">
                    <button onclick="sendChip('Cosa dice la Direttiva EU 2023/970?')"
                            class="px-4 py-2 rounded-full border border-gray-200 bg-white text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 active:bg-gray-100 transition-colors shadow-sm cursor-pointer">
                        Cosa dice la Direttiva EU 2023/970?
                    </button>
                    <button onclick="sendChip('Cos\'è il gender pay gap?')"
                            class="px-4 py-2 rounded-full border border-gray-200 bg-white text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 active:bg-gray-100 transition-colors shadow-sm cursor-pointer">
                        Cos'è il gender pay gap?
                    </button>
                    <button onclick="sendChip('Quali sono gli obblighi di reporting per le aziende?')"
                            class="px-4 py-2 rounded-full border border-gray-200 bg-white text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 active:bg-gray-100 transition-colors shadow-sm cursor-pointer">
                        Obblighi di reporting
                    </button>
                    <button onclick="sendChip('Quali sanzioni prevede la Direttiva EU per le aziende non conformi?')"
                            class="px-4 py-2 rounded-full border border-gray-200 bg-white text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 active:bg-gray-100 transition-colors shadow-sm cursor-pointer">
                        Sanzioni previste
                    </button>
                </div>

            </div><!-- /#chat-empty-state -->

        </div><!-- /#panel-assistente -->

        <!-- PLACEHOLDER: panel-analisi (Task 5) -->
```

**Step 2: Add JS for empty state + chip handler**

In the `<script>` block, after `switchTab()`, add:

```javascript
    // --- Chat empty state ---
    function updateChatEmptyState() {
        var msgs  = document.getElementById('chat-messages');
        var empty = document.getElementById('chat-empty-state');
        if (!msgs || !empty) return;
        var hasMessages = msgs.children.length > 0;
        empty.style.display = hasMessages ? 'none' : '';
        empty.setAttribute('aria-hidden', hasMessages ? 'true' : 'false');
    }

    // --- Chip click → prefill + submit chat form ---
    function sendChip(text) {
        var input = document.getElementById('chat-input');
        var form  = document.getElementById('chat-form');
        if (!input || !form) return;
        input.value = text;
        htmx.trigger(form, 'submit');
    }

    // Init empty states on load
    document.addEventListener('DOMContentLoaded', function() {
        updateChatEmptyState();
    });
```

**Step 3: Verify in browser**

Open `http://localhost:8000`:
- Expected: centered "Come posso aiutarti?" title + subtitle visible
- Expected: 4 suggestion chips visible below
- Expected: chips are clickable (form doesn't exist yet — no crash, but also no submission)

**Step 4: Commit**

```bash
git add templates/index.html
git commit -m "feat: add panel-assistente — empty state, suggestion chips, messages area"
```

---

## Task 5: Add Tab Analisi Dati panel — upload drop zone, results area

**Files:**
- Modify: `templates/index.html`

**Context:** Replace the `<!-- PLACEHOLDER: panel-analisi -->` comment. Same structure as Assistente panel. The upload form lives in the empty state (full-screen drop zone when no results). After the first upload, the empty state hides and results appear in `#analysis-messages`.

**Step 1: Insert the Analisi panel**

Replace `<!-- PLACEHOLDER: panel-analisi (Task 5) -->` with:

```html
        <!-- ============================================================
             PANEL: ANALISI DATI
             ============================================================ -->
        <div id="panel-analisi"
             role="tabpanel"
             aria-labelledby="tab-analisi"
             class="absolute inset-0 flex flex-col hidden">

            <!-- Results area -->
            <main id="analysis-messages"
                  class="flex-1 overflow-y-auto px-4 py-6 pb-28 max-w-3xl mx-auto w-full space-y-4"
                  role="log"
                  aria-live="polite"
                  aria-atomic="false">
            </main>

            <!-- Empty state — big drop zone, disappears after first upload -->
            <div id="analysis-empty-state"
                 class="absolute inset-0 flex flex-col items-center justify-center pb-16">

                <div class="text-center mb-6">
                    <div class="text-5xl mb-4">📊</div>
                    <h2 class="text-[1.5rem] font-semibold text-gray-900 mb-1">
                        Carica i tuoi dati retributivi
                    </h2>
                    <p class="text-gray-500 text-sm">
                        Analisi gender pay gap conforme alla Direttiva EU 2023/970
                    </p>
                </div>

                <form id="upload-form-empty"
                      hx-post="/api/upload"
                      hx-target="#analysis-messages"
                      hx-swap="beforeend"
                      hx-encoding="multipart/form-data"
                      hx-indicator="#thinking"
                      hx-request='{"timeout": 120000}'
                      hx-on::after-request="onUploadAfterRequest(event)"
                      class="w-full max-w-sm px-4">

                    <label class="flex flex-col items-center justify-center w-full h-44 border-2 border-dashed border-gray-300 rounded-2xl bg-white hover:bg-gray-50 hover:border-gray-400 cursor-pointer transition-all group">
                        <svg class="w-9 h-9 text-gray-400 group-hover:text-gray-500 mb-3 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="17 8 12 3 7 8"></polyline>
                            <line x1="12" y1="3" x2="12" y2="15"></line>
                        </svg>
                        <span class="text-sm font-medium text-gray-700">Trascina il file o clicca per caricare</span>
                        <span class="text-xs text-gray-400 mt-1.5">CSV, XLSX, XLS — max 10 MB</span>
                        <input type="file"
                               name="file"
                               accept=".csv,.xlsx,.xls"
                               aria-label="Carica file CSV o Excel"
                               class="hidden"
                               onchange="this.closest('form').requestSubmit();">
                    </label>

                </form>
            </div><!-- /#analysis-empty-state -->

        </div><!-- /#panel-analisi -->
```

**Step 2: Add JS for analysis empty state**

In the `<script>` block, after `updateChatEmptyState()`, add:

```javascript
    // --- Analysis empty state ---
    function updateAnalysisEmptyState() {
        var msgs  = document.getElementById('analysis-messages');
        var empty = document.getElementById('analysis-empty-state');
        if (!msgs || !empty) return;
        var hasResults = msgs.children.length > 0;
        empty.style.display = hasResults ? 'none' : '';
    }

    // --- After upload request ---
    function onUploadAfterRequest(event) {
        if (event.detail.successful) {
            var form = document.getElementById('upload-form-empty') || document.getElementById('upload-form-footer');
            if (form) form.reset();
        }
        var msgs = document.getElementById('analysis-messages');
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
        updateAnalysisEmptyState();
    }
```

Also update `DOMContentLoaded`:
```javascript
    document.addEventListener('DOMContentLoaded', function() {
        updateChatEmptyState();
        updateAnalysisEmptyState();
    });
```

**Step 3: Verify in browser**

Click "Analisi Dati" tab:
- Expected: big drop zone with emoji + title + dashed border visible
- Expected: clicking the zone opens file picker
- Expected: panel-assistente hidden, panel-analisi visible

**Step 4: Commit**

```bash
git add templates/index.html
git commit -m "feat: add panel-analisi — upload drop zone empty state, results area"
```

---

## Task 6: Add thinking indicator + fixed footers (chat input + upload button)

**Files:**
- Modify: `templates/index.html`

**Context:** The thinking indicator is shared between both forms (`hx-indicator="#thinking"`). The footers are fixed at the bottom: Assistente footer has the pill chat input, Analisi footer has a compact upload button. Both footers are controlled by `switchTab()`.

**Step 1: Replace the footer placeholders**

In `index.html`, replace:
```html
    <!-- PLACEHOLDER: thinking indicator (Task 6) -->
    <!-- PLACEHOLDER: footers (Task 6) -->
```

With:

```html
    <!-- ================================================================
         THINKING INDICATOR (shared, htmx-indicator)
         ================================================================ -->
    <div id="thinking"
         class="htmx-indicator fixed bottom-[72px] left-0 right-0 z-40 pointer-events-none"
         role="status"
         aria-live="polite">
        <div class="max-w-3xl mx-auto px-4">
            <div class="flex items-center gap-1.5 py-1">
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></span>
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></span>
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></span>
                <span class="text-xs text-gray-400 ml-1">Elaborazione in corso...</span>
            </div>
        </div>
    </div>

    <!-- ================================================================
         FOOTER: ASSISTENTE — pill chat input
         ================================================================ -->
    <div id="footer-assistente"
         class="fixed bottom-0 left-0 right-0 z-40 pb-4 pt-2"
         style="background: linear-gradient(to top, #F7F7F8 60%, transparent);">
        <form id="chat-form"
              hx-post="/api/chat"
              hx-target="#chat-messages"
              hx-swap="beforeend"
              hx-indicator="#thinking"
              hx-request='{"timeout": 120000}'
              hx-on::after-request="onChatAfterRequest(event)"
              class="max-w-3xl mx-auto px-4">

            <div class="flex items-center gap-2 bg-white rounded-full border border-gray-200 shadow-sm px-4 py-2.5">
                <input type="text"
                       id="chat-input"
                       name="text"
                       placeholder="Scrivi un messaggio..."
                       required
                       autocomplete="off"
                       aria-label="Scrivi un messaggio"
                       class="flex-1 min-h-[32px] bg-transparent focus:outline-none text-sm text-gray-900 placeholder-gray-400">
                <button type="submit"
                        aria-label="Invia messaggio"
                        class="min-w-[34px] min-h-[34px] flex items-center justify-center bg-blue-500 hover:bg-blue-600 active:bg-blue-700 text-white rounded-full transition-colors flex-shrink-0 disabled:opacity-50">
                    <!-- Arrow up icon -->
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <line x1="12" y1="19" x2="12" y2="5"></line>
                        <polyline points="5 12 12 5 19 12"></polyline>
                    </svg>
                </button>
            </div>

        </form>
    </div>

    <!-- ================================================================
         FOOTER: ANALISI DATI — compact upload button
         ================================================================ -->
    <div id="footer-analisi"
         class="fixed bottom-0 left-0 right-0 z-40 pb-4 pt-2 hidden"
         style="background: linear-gradient(to top, #F7F7F8 60%, transparent);">
        <form id="upload-form-footer"
              hx-post="/api/upload"
              hx-target="#analysis-messages"
              hx-swap="beforeend"
              hx-encoding="multipart/form-data"
              hx-indicator="#thinking"
              hx-request='{"timeout": 120000}'
              hx-on::after-request="onUploadAfterRequest(event)"
              class="max-w-3xl mx-auto px-4">

            <label class="flex items-center justify-center gap-2 min-h-[48px] px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 cursor-pointer transition-colors">
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <span>Carica un altro file CSV / Excel</span>
                <input type="file"
                       name="file"
                       accept=".csv,.xlsx,.xls"
                       aria-label="Carica file CSV o Excel"
                       class="hidden"
                       onchange="this.closest('form').requestSubmit();">
            </label>

        </form>
    </div>
```

**Step 2: Add `onChatAfterRequest` to the JS block**

In the `<script>` block, add:

```javascript
    // --- After chat request ---
    function onChatAfterRequest(event) {
        if (event.detail.successful) {
            document.getElementById('chat-form').reset();
        }
        var msgs = document.getElementById('chat-messages');
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
        updateChatEmptyState();
    }
```

**Step 3: Start server and verify complete flow**

```bash
uvicorn app:app --reload --port 8000
```

Checklist (do manually in browser):
- [ ] Header with tabs renders correctly
- [ ] Empty state "Come posso aiutarti?" visible on load
- [ ] 4 chip buttons visible and styled
- [ ] Pill input visible at bottom with arrow-up send button
- [ ] Clicking "Analisi Dati" tab switches panel, shows drop zone, hides chat input, shows upload footer
- [ ] Clicking "Assistente" tab switches back
- [ ] Clicking a chip auto-fills input and submits form (if server is running with RAG initialized)
- [ ] After first message: empty state disappears, messages appear with markdown rendering
- [ ] Dots animation appears during request (htmx-indicator)

**Step 4: Commit**

```bash
git add templates/index.html
git commit -m "feat: add thinking indicator + footer inputs (chat pill + upload button)"
```

---

## Task 7: Final visual polish — spacing, scrollbar, accessibility

**Files:**
- Modify: `templates/base.html` (custom scrollbar CSS)
- Modify: `templates/index.html` (verify aria, padding, mobile)

**Step 1: Add subtle scrollbar CSS to base.html**

In the `<style>` block of `base.html`, after the existing markdown CSS, add:

```css
        /* Subtle scrollbar for messages area */
        #chat-messages::-webkit-scrollbar,
        #analysis-messages::-webkit-scrollbar {
            width: 4px;
        }
        #chat-messages::-webkit-scrollbar-track,
        #analysis-messages::-webkit-scrollbar-track {
            background: transparent;
        }
        #chat-messages::-webkit-scrollbar-thumb,
        #analysis-messages::-webkit-scrollbar-thumb {
            background: #D1D5DB;
            border-radius: 2px;
        }
```

**Step 2: Verify mobile layout**

Open browser DevTools → toggle device toolbar → iPhone 12 Pro (390×844):
- [ ] Header stays fixed and not clipped
- [ ] Chips wrap correctly
- [ ] Pill input not hidden behind browser bottom bar (pb-4 accounts for it)
- [ ] Messages area scrollable

**Step 3: Commit**

```bash
git add templates/base.html templates/index.html
git commit -m "feat: add subtle scrollbar styling and verify mobile layout"
```

---

## Task 8: End-to-end smoke test

**Files:** None (verification only)

**Step 1: Start the server fresh**

```bash
uvicorn app:app --reload --port 8000
```

**Step 2: Run existing test suite to confirm no backend regressions**

```bash
/opt/homebrew/bin/python3.12 -m pytest tests/ -v --ignore=tests/test_web -x -q
# Expected: all passing (63 tests) — template changes don't affect backend tests
```

**Step 3: Manual browser smoke test**

Open `http://localhost:8000`, hard-refresh (Cmd+Shift+R):

| Test | Expected |
|------|----------|
| Load page | Header + empty state + 4 chips |
| Click chip "Cos'è il gender pay gap?" | Input fills, form submits, user bubble appears, dots animate |
| Assistant response renders | Markdown formatted (bold, lists) — not raw asterisks |
| Empty state disappears | After first message, "Come posso aiutarti?" gone |
| Tab → Analisi Dati | Drop zone appears, pill input replaced by upload button |
| Tab → Assistente | Chat messages still there, empty state hidden |
| Upload CSV | Drop zone triggers file picker, result card appears in results area |

**Step 4: If everything passes — done**

```bash
git log --oneline -8
# Review commits from this feature
```

---

## Notes

- **No backend changes.** All HTMX forms still post to `/api/chat` and `/api/upload`. Target IDs `#chat-messages` and `#analysis-messages` match what the partials are injected into.
- **marked.js 9 CDN:** `https://cdn.jsdelivr.net/npm/marked@9/marked.min.js` — pinned to major version 9 for stability.
- **`| tojson` filter:** Jinja2 built-in. Produces a safe JavaScript string literal including quotes — no XSS risk from LLM output in the markdown bubble.
- **HTMX timeout:** Both forms use `hx-request='{"timeout": 120000}'` (120s client) vs 90s server-side `asyncio.wait_for`. This gap ensures the server 504 response renders before HTMX fires `htmx:responseError`.
- **Python version on this machine:** `/opt/homebrew/bin/python3.12` — not `python3` (that's 3.9.6 from CommandLineTools).
