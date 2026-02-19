"""
Agent Router — Fase 3 del progetto Pay Transparency Tool.

Cos'è l'Agent Router?
È il "cervello" dell'applicazione: un agente AI che capisce cosa vuole
l'utente e decide quale strumento usare per rispondere.

L'agent ha 2 tool (strumenti) a disposizione:
1. query_directive  — per domande sulla Direttiva EU (usa il RAG)
2. analyze_pay_gap  — per analisi dati retributivi (usa il GapCalculator)

Esempi di routing:
- "Cosa dice l'Art. 7?"          → usa solo query_directive (RAG)
- "Qual è il gap nel Finance?"   → usa solo analyze_pay_gap (dati)
- "Il gap del 7% è conforme?"   → usa entrambi (ibrida)

Cos'è il "tool calling"?
Il LLM non esegue codice direttamente. Invece:
1. Riceve la domanda + la lista dei tool disponibili (con descrizione)
2. Decide quale tool usare e con quali parametri
3. Il framework chiama il tool e restituisce il risultato al LLM
4. Il LLM formula la risposta finale basandosi sul risultato

Concetti Python usati qui:
- @tool decorator: trasforma una funzione in un "tool" usabile dall'agent
- Agent class: orchestratore che gestisce il ciclo domanda → tool → risposta
- Type annotations + Annotated: descrivono i parametri per il LLM
"""

from typing import Annotated

from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools import tool

from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("agent.router")


# =============================================================================
# SYSTEM PROMPT DELL'AGENT
# =============================================================================
# Questo prompt spiega all'agent CHI è e COME deve comportarsi.
# È diverso dal system prompt del RAG: questo guida il ROUTING,
# non la generazione delle risposte.

AGENT_SYSTEM_PROMPT = """Sei un assistente esperto in trasparenza retributiva e compliance con la Direttiva EU 2023/970.

Hai a disposizione due strumenti:

1. **query_directive** — Per domande sulla normativa EU (articoli, obblighi, scadenze, definizioni).
   Usa questo strumento quando l'utente chiede informazioni sulla Direttiva EU 2023/970.

2. **analyze_pay_gap** — Per analisi dei dati retributivi (calcolo gap, report, compliance check).
   Usa questo strumento quando l'utente vuole analizzare dati salariali da un file CSV/Excel.

REGOLE:
- Se la domanda riguarda la normativa → usa query_directive
- Se la domanda riguarda i dati aziendali → usa analyze_pay_gap
- Se la domanda è ibrida (es. "Il nostro gap del 7% è conforme?") → usa ENTRAMBI gli strumenti
- Rispondi sempre in italiano, in modo chiaro e professionale
- Quando usi risultati di analyze_pay_gap, cita i numeri specifici
- Quando usi risultati di query_directive, cita gli articoli della Direttiva
- Non inventare mai dati o articoli
"""


# =============================================================================
# TOOL: QUERY DIRECTIVE (RAG)
# =============================================================================

@tool(description=(
    "Cerca informazioni nella Direttiva EU 2023/970 sulla trasparenza retributiva. "
    "Usa questo tool per domande su articoli, obblighi, scadenze, definizioni, "
    "sanzioni e qualsiasi aspetto normativo della Direttiva."
))
def query_directive(
    question: Annotated[str, "La domanda sulla Direttiva EU da cercare"]
) -> str:
    """
    Interroga il sistema RAG per rispondere a domande sulla Direttiva EU.

    Internamente:
    1. Cerca i chunk rilevanti nel vector database (Qdrant)
    2. Passa i chunk come contesto al LLM (Groq/Llama)
    3. Genera una risposta con citazioni degli articoli

    Args:
        question: la domanda dell'utente sulla normativa

    Returns:
        Stringa con la risposta del RAG, incluse citazioni e confidenza
    """
    logger.info(f"[Tool] query_directive: '{question}'")

    from src.rag.generator import RAGGenerator

    generator = RAGGenerator()
    response = generator.generate(question, verify=True)

    # Formatta il risultato in modo che l'agent possa usarlo
    result_parts = [
        f"Risposta dalla Direttiva EU 2023/970:\n{response.answer}",
        f"\nConfidenza: {response.confidence:.0%}",
    ]

    if response.verified is not None:
        status = "Verificata" if response.verified else "Non verificata"
        result_parts.append(f"Verifica anti-allucinazione: {status}")

    if response.sources:
        result_parts.append(f"Fonti consultate: {len(response.sources)} chunk del documento")

    return "\n".join(result_parts)


# =============================================================================
# TOOL: ANALYZE PAY GAP (Dati)
# =============================================================================

@tool(description=(
    "Analizza i dati retributivi da un file CSV/Excel e calcola il gender pay gap. "
    "Usa questo tool per calcolare gap salariali, verificare la compliance, "
    "analizzare i quartili retributivi o i bonus. "
    "Il file predefinito è 'data/demo/demo_employees.csv'."
))
def analyze_pay_gap(
    file_path: Annotated[str, "Percorso del file CSV/Excel con i dati retributivi"] = "data/demo/demo_employees.csv",
    analysis_type: Annotated[str, (
        "Tipo di analisi: 'full' per report completo, 'overall' per solo gap complessivo, "
        "'category' per gap per categoria, 'quartiles' per distribuzione quartili, "
        "'bonus' per gap bonus, 'compliance' per verifica compliance"
    )] = "full",
) -> str:
    """
    Carica dati retributivi e calcola il gender pay gap.

    Args:
        file_path: percorso del file CSV/Excel
        analysis_type: tipo di analisi da eseguire

    Returns:
        Stringa con i risultati dell'analisi formattati
    """
    logger.info(f"[Tool] analyze_pay_gap: file='{file_path}', tipo='{analysis_type}'")

    from src.analysis.data_loader import PayDataLoader, DataLoadError, DataValidationError
    from src.analysis.gap_calculator import GapCalculator

    # Step 1: Carica i dati
    try:
        loader = PayDataLoader()
        load_result = loader.load(file_path)
    except (DataLoadError, DataValidationError) as e:
        return f"Errore nel caricamento dati: {e}"

    # Step 2: Calcola
    calculator = GapCalculator(load_result.df)

    # Step 3: Formatta il risultato in base al tipo di analisi
    if analysis_type == "overall":
        return _format_overall(calculator, load_result)
    elif analysis_type == "category":
        return _format_categories(calculator)
    elif analysis_type == "quartiles":
        return _format_quartiles(calculator)
    elif analysis_type == "bonus":
        return _format_bonus(calculator)
    elif analysis_type == "compliance":
        return _format_compliance(calculator)
    else:  # "full" o qualsiasi altro valore
        return _format_full(calculator, load_result)


# =============================================================================
# FUNZIONI DI FORMATTAZIONE RISULTATI
# =============================================================================
# Queste funzioni trasformano i risultati del GapCalculator in stringhe
# leggibili che l'agent può usare per formulare la risposta finale.

def _format_overall(calculator, load_result) -> str:
    """Formatta il gap complessivo."""
    mean = calculator.overall_mean_gap()
    median = calculator.overall_median_gap()

    return (
        f"Analisi Gender Pay Gap — Dataset: {load_result.source_file}\n"
        f"Dipendenti: {load_result.n_employees} ({load_result.n_male} M, {load_result.n_female} F)\n"
        f"\nGap medio complessivo (mean): {mean.gap_pct:+.1f}%\n"
        f"  Media uomini: €{mean.male_avg:,.0f} | Media donne: €{mean.female_avg:,.0f}\n"
        f"\nGap mediano complessivo (median): {median.gap_pct:+.1f}%\n"
        f"  Mediana uomini: €{median.male_avg:,.0f} | Mediana donne: €{median.female_avg:,.0f}\n"
        f"\nSoglia EU: 5%. "
        f"{'ATTENZIONE: il gap mediano supera la soglia.' if abs(median.gap_pct) > 5 else 'Il gap mediano è entro la soglia.'}"
    )


def _format_categories(calculator) -> str:
    """Formatta il gap per categoria."""
    gaps = calculator.gap_by_category()
    if not gaps:
        return "Gap per categoria non disponibile (colonne department/level mancanti)."

    lines = ["Gap per Categoria (Dipartimento + Livello):\n"]
    for cat in gaps:
        flag = "ALERT" if cat.is_significant else "OK"
        lines.append(
            f"  [{flag}] {cat.department} {cat.level}: {cat.gap_pct:+.1f}% "
            f"(M: €{cat.male_avg:,.0f}, F: €{cat.female_avg:,.0f}, "
            f"{cat.male_count}M/{cat.female_count}F)"
        )

    alert_count = sum(1 for c in gaps if c.is_significant)
    lines.append(f"\nCategorie con gap > 5% (soglia EU): {alert_count} su {len(gaps)}")
    return "\n".join(lines)


def _format_quartiles(calculator) -> str:
    """Formatta la distribuzione quartili."""
    quartiles = calculator.pay_quartiles()
    labels = {1: "Q1 (basso)", 2: "Q2", 3: "Q3", 4: "Q4 (alto)"}

    lines = ["Distribuzione per Quartili Retributivi:\n"]
    for q in quartiles:
        lines.append(
            f"  {labels.get(q.quartile, f'Q{q.quartile}')}: "
            f"€{q.min_salary:,.0f}-€{q.max_salary:,.0f} | "
            f"M: {q.male_pct}% F: {q.female_pct}% (totale: {q.total})"
        )
    return "\n".join(lines)


def _format_bonus(calculator) -> str:
    """Formatta il gap bonus."""
    bonus = calculator.bonus_gap()
    if bonus is None:
        return "Analisi bonus non disponibile (colonna 'bonus' mancante nel dataset)."

    return (
        f"Gap nei Bonus:\n"
        f"  Bonus gap: {bonus.gap_pct:+.1f}%\n"
        f"  Media bonus uomini: €{bonus.male_avg:,.0f}\n"
        f"  Media bonus donne: €{bonus.female_avg:,.0f}\n"
        f"  Uomini con bonus: {bonus.male_count} | Donne con bonus: {bonus.female_count}\n"
        f"  {'ATTENZIONE: il gap bonus supera la soglia del 5%.' if bonus.is_significant else 'Il gap bonus è entro la soglia del 5%.'}"
    )


def _format_compliance(calculator) -> str:
    """Formatta il risultato di compliance."""
    result = calculator.full_analysis()

    lines = [
        f"Verifica Compliance EU 2023/970:\n",
        f"Stato: {'COMPLIANT' if result.is_compliant else 'NON COMPLIANT'}\n",
        f"Overall mean gap: {result.overall_mean_gap.gap_pct:+.1f}%",
        f"Overall median gap: {result.overall_median_gap.gap_pct:+.1f}%",
    ]

    if not result.is_compliant:
        lines.append(f"\nCategorie non compliant ({len(result.non_compliant_categories)}):")
        for cat in result.non_compliant_categories:
            lines.append(f"  - {cat.department} {cat.level}: {cat.gap_pct:+.1f}%")
        lines.append(
            "\nArt. 10 Direttiva EU 2023/970: è richiesta una valutazione "
            "retributiva congiunta e l'adozione di misure correttive."
        )

    if result.bonus_gap:
        lines.append(f"\nBonus gap: {result.bonus_gap.gap_pct:+.1f}%")

    return "\n".join(lines)


def _format_full(calculator, load_result) -> str:
    """Formatta il report completo (tutte le sezioni)."""
    parts = [
        _format_overall(calculator, load_result),
        "",
        _format_categories(calculator),
        "",
        _format_quartiles(calculator),
        "",
        _format_bonus(calculator),
        "",
        _format_compliance(calculator),
    ]
    return "\n".join(parts)


# =============================================================================
# CLASSE ROUTER
# =============================================================================

class PayTransparencyRouter:
    """
    Agent integrato che unisce RAG (normativa) e analisi dati (pay gap).

    L'agent decide autonomamente quale tool usare in base alla domanda:
    - Domanda sulla normativa → query_directive (RAG)
    - Domanda sui dati → analyze_pay_gap (GapCalculator)
    - Domanda ibrida → entrambi

    Uso:
        router = PayTransparencyRouter()
        answer = router.ask("Qual è la deadline di trasposizione?")
        print(answer)
    """

    def __init__(self):
        """
        Inizializza l'agent con il client LLM e i tool.
        """
        config = Config.get_instance()
        llm_config = config.llm_config

        # Client LLM per l'agent (lo stesso Groq/Llama usato nel RAG)
        client = OpenAIClient(
            api_key=config.api_key,
            model=llm_config.get("model", "llama-3.3-70b-versatile"),
            base_url=llm_config.get("base_url", "https://api.groq.com/openai/v1"),
            temperature=llm_config.get("temperature", 0.1),
        )

        # Crea l'agent con i 2 tool
        self.agent = Agent(
            name="pay_transparency_assistant",
            client=client,
            system_prompt=AGENT_SYSTEM_PROMPT,
            tools=[query_directive, analyze_pay_gap],
            max_steps=5,           # Massimo 5 cicli tool-call (sicurezza)
            terminate_on_text=True, # Si ferma quando genera testo (non tool call)
        )

        logger.info("PayTransparencyRouter inizializzato")

    def ask(self, question: str) -> str:
        """
        Invia una domanda all'agent e restituisce la risposta.

        L'agent decide autonomamente quale tool usare.

        Args:
            question: la domanda dell'utente (in italiano o inglese)

        Returns:
            La risposta completa dell'agent (stringa)
        """
        logger.info(f"Domanda all'agent: '{question}'")

        result = self.agent.run(question)

        # result.text contiene la risposta finale dell'agent
        answer = result.text

        # Log dei tool usati
        if result.tools_used:
            tool_names = [t.tool.name for t in result.tools_used]
            logger.info(f"Tool usati: {tool_names}")

        logger.info("Risposta generata dall'agent")
        return answer
