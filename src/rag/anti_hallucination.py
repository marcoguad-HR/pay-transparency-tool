"""
Anti-Allucinazione — Fase 1.4 del progetto Pay Transparency Tool.

Cos'è l'anti-allucinazione?
I LLM possono "inventare" informazioni che sembrano plausibili ma sono false.
Questo è un problema grave per uno strumento legale: una data sbagliata
o un articolo inventato potrebbe portare a decisioni errate.

Questo modulo prende la risposta del Generator e la VERIFICA:
chiede a un secondo "giudice" LLM di controllare se ogni affermazione
nella risposta è effettivamente supportata dal contesto originale.

Come funziona:
1. Prende: risposta del Generator + contesto (chunk originali)
2. Chiede al LLM: "Questa risposta è supportata dal contesto?"
3. Il LLM risponde con un JSON strutturato:
   - verified: true/false
   - confidence: 0.0-1.0
   - issues: lista di problemi trovati (se presenti)
4. Se la verifica fallisce, segnala il problema

Analogia: è come un fact-checker che rilegge un articolo
confrontandolo con le fonti originali.

Nota: usiamo lo STESSO LLM (Llama 3.3) per generare e verificare.
Non è il massimo (meglio usare un LLM diverso per il check), ma
per un progetto open-source gratuito è un buon compromesso.
"""

import json
from dataclasses import dataclass, field

# Datapizza AI — client per chiamare Groq
from datapizza.clients.openai import OpenAIClient

# Moduli interni
from src.rag.generator import RAGResponse
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("rag.anti_hallucination")

# --- Prompt per il verificatore ---
# Questo prompt trasforma il LLM in un "fact-checker".
# Le istruzioni sono molto precise per ottenere output JSON parsabile.
VERIFICATION_PROMPT = """Sei un verificatore di fatti (fact-checker) specializzato nel diritto europeo.

Il tuo compito è controllare se una RISPOSTA è fedelmente supportata dal CONTESTO fornito.

REGOLE DI VERIFICA:
1. Ogni affermazione nella risposta DEVE avere un riscontro nel contesto.
2. Numeri, date, articoli citati DEVONO corrispondere esattamente al contesto.
3. Se la risposta dice "non ho trovato informazioni sufficienti", è CORRETTA (ammette i propri limiti).
4. Parafrasi fedeli sono accettabili, invenzioni no.

RISPONDI ESCLUSIVAMENTE con un JSON valido in questo formato:
{
    "verified": true o false,
    "confidence": numero da 0.0 a 1.0,
    "reasoning": "spiegazione breve della tua valutazione",
    "issues": ["problema 1", "problema 2"] oppure [] se nessun problema
}

NON aggiungere testo prima o dopo il JSON. Solo il JSON."""


@dataclass
class VerificationResult:
    """
    Risultato della verifica anti-allucinazione.

    Esempio:
        result.verified = True   → la risposta è affidabile
        result.verified = False  → la risposta contiene allucinazioni
        result.confidence = 0.9  → il verificatore è abbastanza sicuro
        result.issues = []       → nessun problema trovato
    """
    verified: bool                              # La risposta è supportata dal contesto?
    confidence: float = 0.0                     # Confidenza del verificatore (0.0-1.0)
    reasoning: str = ""                         # Spiegazione della valutazione
    issues: list[str] = field(default_factory=list)  # Problemi trovati


class HallucinationChecker:
    """
    Verifica se le risposte del RAG sono supportate dal contesto.

    Uso:
        checker = HallucinationChecker()
        result = checker.verify(rag_response)
        if result.verified:
            print("Risposta affidabile!")
        else:
            print(f"Attenzione: {result.issues}")
    """

    def __init__(self):
        """Inizializza il verificatore con un client LLM dedicato."""
        config = Config.get_instance()
        llm_config = config.llm_config

        # Client LLM per la verifica.
        # Usiamo temperature=0.0 per avere risposte il più deterministiche
        # possibile (il fact-checker non deve essere "creativo"!).
        self.client = OpenAIClient(
            api_key=config.api_key,
            model=llm_config.get("model", "llama-3.3-70b-versatile"),
            base_url=llm_config.get("base_url", "https://api.groq.com/openai/v1"),
            temperature=0.0,  # Deterministico per verifiche fattuali
            system_prompt=VERIFICATION_PROMPT,
        )

        logger.info("HallucinationChecker inizializzato")

    def verify(self, rag_response: RAGResponse) -> VerificationResult:
        """
        Verifica se la risposta del RAG è supportata dal contesto.

        Args:
            rag_response: la risposta completa del RAGGenerator,
                         che contiene sia la risposta sia il contesto usato.

        Returns:
            VerificationResult con l'esito della verifica.
        """
        logger.info("Verifica anti-allucinazione in corso...")

        # Se non c'è contesto, non possiamo verificare nulla
        if not rag_response.context_used:
            logger.warning("Nessun contesto disponibile per la verifica")
            return VerificationResult(
                verified=False,
                confidence=0.0,
                reasoning="Nessun contesto disponibile per la verifica",
                issues=["Risposta generata senza contesto"],
            )

        # Costruisci il prompt di verifica
        prompt = self._build_verification_prompt(rag_response)

        # Chiedi al LLM di verificare
        response = self.client.invoke(prompt)
        raw_text = response.text

        # Parsa il JSON dalla risposta del LLM
        result = self._parse_verification(raw_text)

        logger.info(f"Verifica completata: verified={result.verified}, "
                    f"confidence={result.confidence:.0%}")
        if result.issues:
            for issue in result.issues:
                logger.warning(f"  Problema: {issue}")

        return result

    def _build_verification_prompt(self, rag_response: RAGResponse) -> str:
        """
        Costruisce il prompt da inviare al verificatore.

        Include:
        - Il contesto originale (gli stessi chunk usati per generare)
        - La risposta da verificare
        - La domanda originale (per capire se la risposta è pertinente)
        """
        return f"""CONTESTO (fonti originali della Direttiva EU):
<context>
{rag_response.context_used}
</context>

DOMANDA ORIGINALE:
{rag_response.query}

RISPOSTA DA VERIFICARE:
{rag_response.answer}

Analizza se la RISPOSTA è fedelmente supportata dal CONTESTO.
Rispondi SOLO con il JSON richiesto."""

    def _parse_verification(self, raw_text: str) -> VerificationResult:
        """
        Parsa la risposta JSON del verificatore.

        Il LLM dovrebbe restituire un JSON valido, ma non è garantito.
        Se il parsing fallisce, restituiamo un risultato "non verificato"
        con una nota sull'errore — meglio essere cauti che fidarsi ciecamente.

        Strategia di parsing:
        1. Prova a parsare il JSON direttamente
        2. Se fallisce, cerca un JSON dentro il testo (tra { e })
        3. Se fallisce ancora, restituisci "non verificato"
        """
        # Strategia 1: parsing diretto
        try:
            data = json.loads(raw_text.strip())
            return self._json_to_result(data)
        except json.JSONDecodeError:
            pass

        # Strategia 2: cerca JSON nel testo
        # A volte il LLM aggiunge testo prima/dopo il JSON
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(raw_text[start:end])
                return self._json_to_result(data)
            except json.JSONDecodeError:
                pass

        # Strategia 3: fallback — non siamo riusciti a parsare
        logger.warning(f"Impossibile parsare la risposta del verificatore: {raw_text[:200]}")
        return VerificationResult(
            verified=False,
            confidence=0.0,
            reasoning="Errore nel parsing della risposta del verificatore",
            issues=["Il verificatore non ha restituito un JSON valido"],
        )

    def _json_to_result(self, data: dict) -> VerificationResult:
        """
        Converte un dizionario JSON in un VerificationResult.

        Gestisce valori mancanti con default sicuri:
        se un campo non c'è, assumiamo il caso peggiore.
        """
        return VerificationResult(
            verified=data.get("verified", False),
            confidence=float(data.get("confidence", 0.0)),
            reasoning=data.get("reasoning", ""),
            issues=data.get("issues", []),
        )
