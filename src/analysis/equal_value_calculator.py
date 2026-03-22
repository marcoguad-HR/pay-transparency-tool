"""
Equal Value Calculator — Confronto pari valore tra ruoli secondo i criteri SERW.

Implementa la valutazione dei ruoli con 16 sotto-fattori (scala 1-5) raggruppati
in 4 categorie (Skills, Effort, Responsibility, Working Conditions) come previsto
dalla Direttiva EU 2023/970 sulla trasparenza retributiva.
"""
from dataclasses import dataclass, field
from src.utils.logger import get_logger

logger = get_logger("analysis.equal_value_calculator")


@dataclass
class RoleScores:
    """Punteggi SERW per un ruolo (16 sotto-fattori, scala 1-5)."""
    name: str
    # Skills (Competenze)
    S1: int  # Istruzione/qualifiche
    S2: int  # Esperienza
    S3: int  # Conoscenze tecniche
    S4: int  # Capacità interpersonali
    # Effort (Impegno)
    E1: int  # Impegno fisico
    E2: int  # Concentrazione mentale
    E3: int  # Impegno emotivo
    E4: int  # Multi-tasking/pressione tempi
    # Responsibility (Responsabilità)
    R1: int  # Supervisione persone
    R2: int  # Impatto finanziario
    R3: int  # Benessere altrui
    R4: int  # Dati sensibili
    # Working Conditions (Condizioni di lavoro)
    W1: int  # Ambiente fisico/rischi
    W2: int  # Stress psicologico
    W3: int  # Orari disagiati
    W4: int  # Trasferte


@dataclass
class CategoryScore:
    """Score di una categoria SERW per un ruolo."""
    category: str   # "skills", "effort", "responsibility", "working_conditions"
    label: str      # "Competenze", "Impegno", etc.
    score: int      # 4-20 (somma 4 fattori)
    max_score: int = 20
    weight: float = 0.25


@dataclass
class GenderWarning:
    """Warning di gender-neutrality."""
    code: str       # es. "effort_emotional_undervalued"
    message: str    # Messaggio per l'utente
    severity: str   # "warning" o "info"


@dataclass
class ComparisonResult:
    """Risultato del confronto tra 2 ruoli."""
    role_a: RoleScores
    role_b: RoleScores
    score_a: float              # Score totale ruolo A (16-80, pesato)
    score_b: float              # Score totale ruolo B
    difference_pct: float       # |A-B| / max(A,B) * 100
    verdict: str                # "equal", "maybe", "not_equal"
    verdict_label: str          # "Ruoli di PARI VALORE", etc.
    category_scores_a: list[CategoryScore] = field(default_factory=list)
    category_scores_b: list[CategoryScore] = field(default_factory=list)
    warnings: list[GenderWarning] = field(default_factory=list)


# Mapping categorie → fattori e label italiane
_CATEGORY_MAP = {
    "skills":             {"factors": ("S1", "S2", "S3", "S4"), "label": "Competenze"},
    "effort":             {"factors": ("E1", "E2", "E3", "E4"), "label": "Impegno"},
    "responsibility":     {"factors": ("R1", "R2", "R3", "R4"), "label": "Responsabilità"},
    "working_conditions": {"factors": ("W1", "W2", "W3", "W4"), "label": "Condizioni di lavoro"},
}

# Tutti i 16 fattori in ordine
_ALL_FACTORS = [f for cat in _CATEGORY_MAP.values() for f in cat["factors"]]

# Verdetti
_VERDICT_LABELS = {
    "equal": "Ruoli di PARI VALORE",
    "maybe": "Ruoli POTENZIALMENTE COMPARABILI",
    "not_equal": "Ruoli NON di pari valore",
}


class EqualValueCalculator:
    """Calcola e confronta il valore di 2 ruoli secondo i criteri SERW."""

    # Default pesi e soglie (override da config.yaml se presente)
    DEFAULT_WEIGHTS = {
        "skills": 0.25,
        "effort": 0.25,
        "responsibility": 0.25,
        "working_conditions": 0.25,
    }
    DEFAULT_THRESHOLD_EQUAL = 10.0
    DEFAULT_THRESHOLD_MAYBE = 20.0

    def __init__(self):
        """Carica config da YAML se disponibile, altrimenti usa defaults."""
        self.weights = dict(self.DEFAULT_WEIGHTS)
        self.threshold_equal = self.DEFAULT_THRESHOLD_EQUAL
        self.threshold_maybe = self.DEFAULT_THRESHOLD_MAYBE

        try:
            from src.utils.config import Config
            config = Config.get_instance()
            ev_config = getattr(config, "equal_value", None)
            if ev_config and isinstance(ev_config, dict):
                if "weights" in ev_config:
                    self.weights.update(ev_config["weights"])
                if "threshold_equal" in ev_config:
                    self.threshold_equal = float(ev_config["threshold_equal"])
                if "threshold_maybe" in ev_config:
                    self.threshold_maybe = float(ev_config["threshold_maybe"])
        except Exception:
            # Config non disponibile (es. in test) — uso defaults
            pass

    def validate_scores(self, role: RoleScores) -> None:
        """Valida che tutti i punteggi siano 1-5. Raise ValueError se no."""
        for factor in _ALL_FACTORS:
            val = getattr(role, factor)
            if not isinstance(val, int) or val < 1 or val > 5:
                raise ValueError(
                    f"Punteggio {factor}={val} per il ruolo '{role.name}' "
                    f"fuori range. I punteggi devono essere interi tra 1 e 5."
                )

    def calculate_category_scores(self, role: RoleScores) -> list[CategoryScore]:
        """Calcola lo score per ciascuna delle 4 categorie SERW."""
        result = []
        for cat_key, cat_info in _CATEGORY_MAP.items():
            score = sum(getattr(role, f) for f in cat_info["factors"])
            result.append(CategoryScore(
                category=cat_key,
                label=cat_info["label"],
                score=score,
                weight=self.weights.get(cat_key, 0.25),
            ))
        return result

    def calculate_total_score(self, role: RoleScores) -> float:
        """Calcola lo score totale pesato (16-80 con pesi uguali).

        Con pesi uguali (0.25 ciascuno), il totale e' la somma dei 16 fattori.
        Con pesi diversi: somma(category_score * weight * 4) per normalizzare.
        """
        cats = self.calculate_category_scores(role)
        # Peso normalizzato: score_cat * (weight / 0.25) = score_cat * weight * 4
        total = sum(c.score * c.weight * 4 for c in cats)
        return total

    def check_gender_warnings(self, role: RoleScores) -> list[GenderWarning]:
        """Controlla bias di genere nei punteggi di un singolo ruolo."""
        warnings: list[GenderWarning] = []

        # 1. Sforzo emotivo sottovalutato: E1 >= 4 e E3 <= 2
        if role.E1 >= 4 and role.E3 <= 2:
            warnings.append(GenderWarning(
                code="effort_emotional_undervalued",
                message=(
                    f"Attenzione: per '{role.name}' l'impegno fisico (E1={role.E1}) "
                    f"è valutato molto più dell'impegno emotivo (E3={role.E3}). "
                    f"L'impegno emotivo è spesso sottovalutato in lavori a prevalenza femminile."
                ),
                severity="warning",
            ))

        # 2. Benessere altrui sottovalutato: R2 >= 4 e R3 <= 2
        if role.R2 >= 4 and role.R3 <= 2:
            warnings.append(GenderWarning(
                code="responsibility_wellbeing_undervalued",
                message=(
                    f"Attenzione: per '{role.name}' l'impatto finanziario (R2={role.R2}) "
                    f"è valutato molto più del benessere altrui (R3={role.R3}). "
                    f"La responsabilità per il benessere è spesso sottovalutata."
                ),
                severity="warning",
            ))

        # 3. Stress psicologico sottovalutato: W1 >= 4 e W2 <= 2
        if role.W1 >= 4 and role.W2 <= 2:
            warnings.append(GenderWarning(
                code="working_conditions_psychological_undervalued",
                message=(
                    f"Attenzione: per '{role.name}' i rischi fisici (W1={role.W1}) "
                    f"sono valutati molto più dello stress psicologico (W2={role.W2}). "
                    f"Lo stress psicologico è spesso sottovalutato."
                ),
                severity="warning",
            ))

        # 4. Dominanza di un singolo fattore in una categoria (> 40% del totale)
        for cat_key, cat_info in _CATEGORY_MAP.items():
            factors = cat_info["factors"]
            values = [getattr(role, f) for f in factors]
            total = sum(values)
            if total == 0:
                continue
            for f, v in zip(factors, values):
                ratio = v / total
                if ratio > 0.40:
                    warnings.append(GenderWarning(
                        code=f"{cat_key}_{f}_dominance",
                        message=(
                            f"Il fattore {f}={v} rappresenta il {ratio:.0%} "
                            f"della categoria '{cat_info['label']}' per '{role.name}'. "
                            f"Verificare che i punteggi riflettano criteri gender-neutral."
                        ),
                        severity="info",
                    ))

        return warnings

    def compare(self, role_a: RoleScores, role_b: RoleScores) -> ComparisonResult:
        """Confronta 2 ruoli e restituisce il verdetto."""
        # Validazione
        self.validate_scores(role_a)
        self.validate_scores(role_b)

        # Calcoli
        score_a = self.calculate_total_score(role_a)
        score_b = self.calculate_total_score(role_b)
        cats_a = self.calculate_category_scores(role_a)
        cats_b = self.calculate_category_scores(role_b)

        # Differenza percentuale
        max_score = max(score_a, score_b)
        if max_score == 0:
            difference_pct = 0.0
        else:
            difference_pct = abs(score_a - score_b) / max_score * 100

        # Verdetto
        if difference_pct <= self.threshold_equal:
            verdict = "equal"
        elif difference_pct <= self.threshold_maybe:
            verdict = "maybe"
        else:
            verdict = "not_equal"

        # Warnings combinati da entrambi i ruoli
        warnings = self.check_gender_warnings(role_a) + self.check_gender_warnings(role_b)

        logger.info(
            f"Confronto '{role_a.name}' vs '{role_b.name}': "
            f"score {score_a:.1f} vs {score_b:.1f}, diff {difference_pct:.1f}%, "
            f"verdetto={verdict}, {len(warnings)} warning(s)"
        )

        return ComparisonResult(
            role_a=role_a,
            role_b=role_b,
            score_a=score_a,
            score_b=score_b,
            difference_pct=round(difference_pct, 2),
            verdict=verdict,
            verdict_label=_VERDICT_LABELS[verdict],
            category_scores_a=cats_a,
            category_scores_b=cats_b,
            warnings=warnings,
        )
