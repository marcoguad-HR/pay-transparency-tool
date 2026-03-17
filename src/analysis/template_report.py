"""
Template Report — Report pay gap in Markdown, senza LLM.

Genera un report completo del gender pay gap in formato Markdown,
partendo dal ComplianceResult del GapCalculator. Il report viene
renderizzato da marked.js nella chat bubble del frontend.

Perche' questo modulo?
La Direttiva EU 2023/970 richiede trasparenza ma i dati retributivi
sono sensibili. Questo modulo produce il report interamente server-side,
senza inviare alcun dato a API esterne (zero chiamate LLM).

Usato da: src/web/api/chat.py (path template per query di analisi dati)
"""

from src.analysis.gap_calculator import ComplianceResult, CategoryGap, QuartileData


def generate_markdown_report(result: ComplianceResult, load_result) -> str:
    """
    Genera un report markdown completo dal ComplianceResult.

    Args:
        result: output di GapCalculator.full_analysis()
        load_result: output di PayDataLoader.load() (per metadata)

    Returns:
        Stringa markdown pronta per marked.js
    """
    sections = [
        _format_status(result, load_result),
        _format_kpi(result),
        _format_categories(result.category_gaps),
        _format_quartiles(result.quartiles),
        _format_next_steps(result),
        _format_disclaimer(load_result.source_file),
    ]
    return "\n\n".join(s for s in sections if s)


# ---------------------------------------------------------------------------
# Sezioni del report
# ---------------------------------------------------------------------------

def _gap_indicator(gap_pct: float) -> str:
    """Indicatore testuale per il gap."""
    abs_gap = abs(gap_pct)
    if gap_pct < 0:
        return "Invertito"
    if abs_gap <= 5:
        return "Nella soglia"
    if abs_gap <= 10:
        return "Supera il 5%"
    return "Gap significativo"


def _format_status(result: ComplianceResult, load_result) -> str:
    if result.is_compliant:
        return (
            f"### Risultato: Conforme\n\n"
            f"Nessun gap retributivo supera la **soglia del 5%** "
            f"richiesta dalla Direttiva EU 2023/970.\n\n"
            f"*{load_result.source_file}* — "
            f"{load_result.n_employees} dipendenti "
            f"({load_result.n_male} uomini, {load_result.n_female} donne)"
        )

    n_crit = len(result.non_compliant_categories)
    cat_word = "categoria presenta" if n_crit == 1 else "categorie presentano"
    return (
        f"### Risultato: Non Conforme\n\n"
        f"**{n_crit} {cat_word}** un gap retributivo superiore al 5%.\n"
        f"Art. 9 Direttiva EU: e' richiesta una valutazione retributiva congiunta "
        f"entro **6 mesi** dalla rilevazione.\n\n"
        f"*{load_result.source_file}* — "
        f"{load_result.n_employees} dipendenti "
        f"({load_result.n_male} uomini, {load_result.n_female} donne)"
    )


def _format_kpi(result: ComplianceResult) -> str:
    mean = result.overall_mean_gap
    median = result.overall_median_gap

    lines = [
        "### Indicatori Principali",
        "",
        f"| Metrica | Gap | Uomini | Donne | Stato |",
        f"|---------|-----|--------|-------|-------|",
        f"| Gap Medio | {mean.gap_pct:+.1f}% | EUR {mean.male_avg:,.0f} | EUR {mean.female_avg:,.0f} | {_gap_indicator(mean.gap_pct)} |",
        f"| Gap Mediano | {median.gap_pct:+.1f}% | EUR {median.male_avg:,.0f} | EUR {median.female_avg:,.0f} | {_gap_indicator(median.gap_pct)} |",
    ]

    if result.bonus_gap:
        b = result.bonus_gap
        lines.append(
            f"| Gap Bonus | {b.gap_pct:+.1f}% | EUR {b.male_avg:,.0f} | EUR {b.female_avg:,.0f} | {_gap_indicator(b.gap_pct)} |"
        )

    return "\n".join(lines)


def _format_categories(category_gaps: list[CategoryGap]) -> str:
    if not category_gaps:
        return ""

    sorted_cats = sorted(category_gaps, key=lambda c: c.gap_pct, reverse=True)

    lines = [
        "### Gap per Ruolo e Dipartimento",
        "",
        "| Dipartimento | Livello | Gap | Media M | Media F | Stato |",
        "|-------------|---------|-----|---------|---------|-------|",
    ]

    for cat in sorted_cats:
        lines.append(
            f"| {cat.department} | {cat.level} | {cat.gap_pct:+.1f}% "
            f"| EUR {cat.male_avg:,.0f} | EUR {cat.female_avg:,.0f} "
            f"| {_gap_indicator(cat.gap_pct)} |"
        )

    n_alert = sum(1 for c in category_gaps if c.is_significant)
    if n_alert:
        lines.append(f"\n**{n_alert} categorie** superano la soglia EU del 5%.")

    return "\n".join(lines)


def _format_quartiles(quartiles: list[QuartileData]) -> str:
    if not quartiles:
        return ""

    labels = {1: "Q1 — Bassi", 2: "Q2 — Medio-Bassi", 3: "Q3 — Medio-Alti", 4: "Q4 — Alti"}
    sorted_q = sorted(quartiles, key=lambda q: q.quartile, reverse=True)

    lines = [
        "### Distribuzione Quartili Salariali",
        "",
        "| Quartile | Range | % Uomini | % Donne |",
        "|----------|-------|----------|---------|",
    ]

    for q in sorted_q:
        lines.append(
            f"| {labels.get(q.quartile, f'Q{q.quartile}')} "
            f"| EUR {q.min_salary:,.0f} – {q.max_salary:,.0f} "
            f"| {q.male_pct}% | {q.female_pct}% |"
        )

    # Interpretazione automatica
    by_quartile = sorted(quartiles, key=lambda q: q.quartile)
    q1 = by_quartile[0]
    q4 = by_quartile[-1]

    if q4.male_pct > 60:
        lines.append(
            "\nIl gap e' maggiore nelle **fasce alte**: "
            "poche donne raggiungono i ruoli e le retribuzioni piu' elevate."
        )
    elif q1.female_pct > 60:
        lines.append(
            "\nLe donne sono **sovrarappresentate nella fascia piu' bassa**: "
            "piu' della meta' dei lavoratori a bassa retribuzione sono donne."
        )
    else:
        lines.append(
            "\nLa distribuzione e' **relativamente uniforme** "
            "tra le fasce retributive."
        )

    return "\n".join(lines)


def _format_next_steps(result: ComplianceResult) -> str:
    if result.is_compliant:
        return (
            "### Prossimi Passi\n\n"
            "1. Conserva questo report come documentazione di compliance\n"
            "2. Ripeti l'analisi almeno una volta l'anno "
            "(obbligatorio per aziende con 250+ dipendenti)\n"
            "3. Monitora le categorie con gap tra 3-5%: "
            "sono nella soglia ma potrebbero sforare\n\n"
            "*Riferimento: Art. 9, Direttiva EU 2023/970*"
        )

    has_high = any(c.gap_pct > 10 for c in result.category_gaps)

    lines = ["### Prossimi Passi — Azione Richiesta", ""]
    lines.append(
        "Hai **6 mesi** dalla data di rilevazione "
        "per avviare le azioni correttive."
    )

    if has_high:
        lines.extend([
            "",
            "**Priorita' Alta (gap > 10%):**",
            "1. Esegui un'analisi dettagliata del ruolo specifico",
            "2. Documenta le ragioni oggettive della differenza",
            "3. Prepara un piano di adeguamento retributivo",
        ])

    lines.extend([
        "",
        "**Azioni obbligatorie:**",
        "1. Avvia una valutazione retributiva congiunta "
        "con i rappresentanti dei dipendenti",
        "2. Rivedi le pratiche di assunzione e promozione",
        "3. Documenta il processo di revisione",
        "",
        "*Riferimento: Art. 9-10, Direttiva EU 2023/970*",
    ])

    return "\n".join(lines)


def _format_disclaimer(source_file: str) -> str:
    if "demo" in source_file.lower():
        return (
            "---\n\n"
            "*Questa analisi e' basata sul dataset demo. "
            "Per analizzare i tuoi dati in modo privato, "
            "vai sulla tab \"Analisi Dati\" e carica il tuo file CSV/Excel. "
            "I dati non vengono mai inviati a servizi esterni.*"
        )
    return (
        "---\n\n"
        "*Questa analisi e' stata generata interamente server-side. "
        "Nessun dato e' stato inviato a servizi esterni.*"
    )
