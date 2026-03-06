"""
Generator — Fase 1.3 del progetto Pay Transparency Tool.

Cos'è il Generator nel RAG?
È il componente che prende i chunk trovati dal Retriever e li passa
a un LLM (Llama 3.3 via Groq) per generare una risposta in linguaggio naturale.

Il trucco del RAG è qui: invece di chiedere al LLM di rispondere
"a memoria" (rischiando allucinazioni), gli diamo il CONTESTO
estratto dai documenti reali e gli diciamo:
"Rispondi SOLO basandoti su questo contesto."

Schema:
    Domanda utente + Chunk rilevanti → Prompt → LLM → Risposta con citazioni

Concetti chiave:
- System Prompt: le "regole" che il LLM deve seguire (es. "non inventare")
- Contesto: i chunk del Retriever, formattati come testo
- Confidence Score: una stima di quanto la risposta è affidabile,
  basata su quanti chunk supportano la risposta
- Citazione: riferimento al documento/articolo da cui viene la risposta
"""

from dataclasses import dataclass, field

# Datapizza AI — client per chiamare Groq (API compatibile OpenAI)
from datapizza.clients.openai import OpenAIClient

# Moduli interni
from src.rag.retriever import DirectiveRetriever, RetrievalResult
from src.rag.query_transformer import QueryTransformer
from src.utils.config import Config
from src.utils.logger import get_logger
from src.utils.rate_limiter import invoke_with_retry

logger = get_logger("rag.generator")

# --- System Prompt Anti-Allucinazione ---
# Questo è il prompt più importante di tutto il progetto.
# Dice al LLM COME deve comportarsi: rispondere solo dal contesto,
# citare le fonti, ammettere quando non sa qualcosa.
SYSTEM_PROMPT = """Sei un consulente esperto in trasparenza retributiva e nella Direttiva EU 2023/970 (Pay Transparency Directive).
Il tuo ruolo è aiutare HR manager e professionisti italiani a capire COSA DEVONO FARE concretamente per essere conformi alla normativa.

COME RISPONDERE:
1. Parti sempre dal contesto fornito tra i tag <context> e </context> come base fattuale.
2. Cita l'articolo o la sezione della Direttiva da cui proviene l'informazione.
3. Dopo aver citato la normativa, AGGIUNGI SEMPRE un'interpretazione pratica:
   - Cosa significa concretamente per l'azienda dell'utente
   - Quali azioni specifiche dovrebbe intraprendere
   - Eventuali tempistiche da rispettare
   - Se l'utente menziona la dimensione della sua azienda, adatta la risposta agli obblighi specifici per quella fascia
4. Se il contesto non contiene informazioni sufficienti, dì chiaramente: "Non ho trovato informazioni sufficienti nel contesto disponibile per rispondere a questa domanda."
5. NON inventare mai articoli, numeri o date non presenti nel contesto.
6. Rispondi nella stessa lingua della domanda.

DISTINZIONI IMPORTANTI (usa queste etichette nelle risposte):
- **Obbligo normativo**: quando qualcosa è esplicitamente richiesto dalla Direttiva EU
- **In attesa del decreto italiano**: quando l'applicazione specifica dipenderà dal recepimento italiano
- **Buona pratica consigliata**: quando suggerisci azioni non obbligatorie ma raccomandate

FORMATO:
- Usa un tono professionale ma accessibile (non legalese)
- Struttura la risposta in modo chiaro con punti chiave
- Quando possibile, concludi con un "In sintesi" o "Prossimi passi" che riassuma le azioni concrete
"""


@dataclass
class RAGResponse:
    """
    Risposta generata dal sistema RAG.

    Contiene non solo il testo della risposta, ma anche metadati utili:
    - I chunk usati come contesto (per verificabilità)
    - Un punteggio di confidenza (per capire se fidarsi)
    - La query originale (per tracciabilità)
    """
    answer: str                                      # La risposta generata dal LLM
    query: str                                       # La domanda originale
    confidence: float = 0.0                          # 0.0 = bassa, 1.0 = alta
    sources: list[RetrievalResult] = field(default_factory=list)  # Chunk usati
    context_used: str = ""                           # Il contesto formattato inviato al LLM
    verified: bool | None = None                     # None = non verificato, True/False = esito
    verification_reasoning: str = ""                 # Spiegazione della verifica


class RAGGenerator:
    """
    Genera risposte basate sul contesto recuperato dal Retriever.

    Pipeline interna:
    1. Riceve query → passa al Retriever → ottiene chunk
    2. Formatta i chunk come contesto testuale
    3. Costruisce il prompt (system + contesto + domanda)
    4. Chiama Llama 3.3 via Groq
    5. Calcola un confidence score
    6. Restituisce RAGResponse

    Uso:
        generator = RAGGenerator()
        response = generator.generate("Qual è la deadline di trasposizione?")
        print(response.answer)
        print(f"Confidenza: {response.confidence:.0%}")
    """

    def __init__(self):
        """
        Inizializza il Generator con Retriever e client LLM.
        """
        config = Config.get_instance()
        llm_config = config.llm_config

        # --- Retriever: cerca i chunk rilevanti ---
        self.retriever = DirectiveRetriever()

        # --- Query Transformer: step-back prompting (opzionale) ---
        self.query_transformer = QueryTransformer()

        # --- Client LLM: Groq con Llama 3.3 ---
        # OpenAIClient di Datapizza AI funziona con Groq grazie a base_url.
        # Il system_prompt viene inviato come "istruzioni" al modello.
        self.client = OpenAIClient(
            api_key=config.api_key,
            model=llm_config.get("model", "llama-3.3-70b-versatile"),
            base_url=llm_config.get("base_url", "https://api.groq.com/openai/v1"),
            temperature=llm_config.get("temperature", 0.1),
            system_prompt=SYSTEM_PROMPT,
        )

        # Soglia minima di confidenza (sotto questa, la risposta è "incerta")
        rag_config = config.rag_config
        self.confidence_threshold = rag_config.get("confidence_threshold", 0.6)

        # Cache per HallucinationChecker (lazy init alla prima verifica)
        self._checker = None

        logger.info("Generator inizializzato con Groq/Llama 3.3")

    def generate(self, query: str, top_k: int | None = None, verify: bool = False) -> RAGResponse:
        """
        Genera una risposta alla domanda usando il pipeline RAG completo.

        Args:
            query: la domanda dell'utente
            top_k: quanti chunk usare come contesto (default da config)
            verify: se True, verifica la risposta con l'anti-allucinazione.
                    Costa una chiamata LLM in più, ma aumenta l'affidabilità.

        Returns:
            RAGResponse con risposta, fonti, confidenza e (opzionale) verifica
        """
        logger.info(f"Generazione risposta per: '{query}'")

        # Step 0.5: Trasformazione query (se abilitata)
        transformed = self.query_transformer.transform(query)

        # Step 1: Recupera i chunk più rilevanti con la query originale
        results = self.retriever.retrieve(transformed.original, top_k=top_k)

        # Step 1.5: Se step-back query disponibile, recupera contesto aggiuntivo
        if transformed.step_back:
            step_back_results = self.retriever.retrieve(transformed.step_back, top_k=top_k)
            # Merge: deduplica per chunk_id, mantieni l'ordine
            seen_ids = {r.chunk_id for r in results}
            for r in step_back_results:
                if r.chunk_id not in seen_ids:
                    results.append(r)
                    seen_ids.add(r.chunk_id)
            # Limita per non sovraccaricare il contesto
            k = top_k or self.retriever.top_k
            results = results[:int(k * 1.5)]

        if not results:
            logger.warning("Nessun chunk trovato! Il vector DB potrebbe essere vuoto.")
            return RAGResponse(
                answer="Non ho trovato informazioni nel database. "
                       "Assicurati di aver eseguito l'ingestion dei documenti.",
                query=query,
                confidence=0.0,
                sources=[],
            )

        # Step 2: Formatta i chunk come contesto testuale
        context = self._format_context(results)

        # Step 3: Costruisci il prompt utente (contesto + domanda)
        user_prompt = self._build_prompt(context, query)

        # Step 4: Chiama il LLM
        logger.info("Invio al LLM...")
        response = invoke_with_retry(self.client, user_prompt)
        answer = response.text

        # Step 5: Calcola confidence score
        confidence = self._compute_confidence(results, answer)

        logger.info(f"Risposta generata (confidenza: {confidence:.0%})")

        rag_response = RAGResponse(
            answer=answer,
            query=query,
            confidence=confidence,
            sources=results,
            context_used=context,
        )

        # Step 6 (opzionale): Verifica anti-allucinazione
        if verify:
            if self._checker is None:
                from src.rag.anti_hallucination import HallucinationChecker
                self._checker = HallucinationChecker()
            verification = self._checker.verify(rag_response)

            rag_response.verified = verification.verified
            rag_response.verification_reasoning = verification.reasoning

            # Se la verifica trova problemi, abbassa la confidenza
            if not verification.verified:
                rag_response.confidence = min(rag_response.confidence, 0.3)
                logger.warning(f"Verifica FALLITA: {verification.reasoning}")

        return rag_response

    def _format_context(self, results: list[RetrievalResult]) -> str:
        """
        Formatta i chunk del Retriever in un blocco di contesto per il LLM.

        Ogni chunk viene numerato e separato, così il LLM può riferirsi
        a "Fonte 1", "Fonte 2", ecc. nella sua risposta.

        Esempio output:
            [Fonte 1] (da: CELEX_32023L0970_EN_TXT.pdf)
            Article 34 Transposition...

            [Fonte 2] (da: CELEX_32023L0970_EN_TXT.pdf)
            Article 9 Reporting on pay gap...
        """
        context_parts = []

        for i, result in enumerate(results, 1):
            # Estrai solo il nome del file dal percorso completo
            source_name = result.source.split("/")[-1] if result.source else "sconosciuto"

            header_info = f" | {result.article_header}" if result.article_header else ""
            context_parts.append(
                f"[Fonte {i}] (da: {source_name}{header_info})\n{result.text}"
            )

        return "\n\n---\n\n".join(context_parts)

    def _build_prompt(self, context: str, query: str) -> str:
        """
        Costruisce il prompt utente da inviare al LLM.

        Il prompt ha una struttura precisa:
        1. Tag <context> con il contesto (i chunk)
        2. La domanda dell'utente

        I tag <context> servono a delimitare chiaramente dove inizia
        e finisce il contesto, così il LLM non lo confonde con la domanda.
        """
        return f"""<context>
{context}
</context>

Domanda: {query}"""

    def _compute_confidence(self, results: list[RetrievalResult], answer: str) -> float:
        """
        Calcola un punteggio di confidenza per la risposta.

        Logica semplice (v1):
        - Parte da 0.5 (base)
        - +0.1 per ogni chunk usato (più contesto = più sicurezza)
        - -0.3 se la risposta contiene "non ho trovato" (ammette di non sapere)
        - Cap a 1.0 massimo

        In futuro (Fase 1.4) useremo un approccio più sofisticato
        con verifica LLM-based (anti-allucinazione).
        """
        confidence = 0.5

        # Più chunk rilevanti trovati = più sicurezza
        # (fino a +0.5 con 5 chunk)
        confidence += min(len(results) * 0.1, 0.5)

        # Se la risposta ammette di non sapere, abbassa la confidenza
        # (è comunque un segnale positivo: meglio ammettere che inventare)
        no_info_phrases = [
            "non ho trovato",
            "informazioni sufficienti",
            "non sono in grado",
            "not found",
            "insufficient information",
        ]
        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in no_info_phrases):
            confidence -= 0.3

        # Limita tra 0.0 e 1.0
        return max(0.0, min(1.0, confidence))
