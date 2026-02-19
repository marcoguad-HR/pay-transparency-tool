"""
Report Formatter — Fase 2.4 del progetto Pay Transparency Tool.

Questo modulo trasforma i risultati del GapCalculator in un report visuale
formattato con tabelle, colori e panel nel terminale.

Usiamo la libreria 'rich' che permette di creare output colorato e
strutturato nel terminale — molto più leggibile di semplici print().

Concetti Python usati qui:
- rich.table.Table: crea tabelle formattate con bordi, colori e allineamento
- rich.panel.Panel: box con bordo e titolo per evidenziare informazioni
- rich.console.Console: il "motore" che stampa tutto nel terminale
- rich.text.Text: testo con stile (grassetto, colori, ecc.)
- Conditional styling: colori diversi in base ai valori (rosso=alert, verde=ok)
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.analysis.gap_calculator import ComplianceResult


# Console globale per l'output
console = Console()


class PayGapReport:
    """
    Genera report formattati del gender pay gap nel terminale.

    Prende un ComplianceResult (output del GapCalculator) e lo trasforma
    in tabelle e panel colorati.

    Uso:
        result = calculator.full_analysis()
        report = PayGapReport(result)
        report.print_full_report()
    """

    def __init__(self, result: ComplianceResult):
        """
        Args:
            result: il ComplianceResult prodotto da GapCalculator.full_analysis()
        """
        self.result = result

    def print_full_report(self) -> None:
        """Stampa il report completo con tutte le sezioni."""
        self._print_header()
        self._print_overall_gap()
        self._print_category_gaps()
        self._print_quartiles()
        self._print_bonus_gap()
        self._print_compliance_summary()

    def _print_header(self) -> None:
        """Stampa l'intestazione del report."""
        console.print()
        title = Text("GENDER PAY GAP REPORT", style="bold white")
        subtitle = Text("Analisi ai sensi della Direttiva EU 2023/970", style="dim")
        content = Text.assemble(title, "\n", subtitle)
        console.print(Panel(content, border_style="blue", padding=(1, 2)))

    def _print_overall_gap(self) -> None:
        """
        Stampa il gap complessivo (mean e median) in un panel.

        Colori:
        - Verde: gap <= 5% (compliant)
        - Giallo: gap tra 5% e 10% (attenzione)
        - Rosso: gap > 10% (critico)
        """
        mean = self.result.overall_mean_gap
        median = self.result.overall_median_gap

        table = Table(title="Gap Retributivo Complessivo", show_header=True)
        table.add_column("Metrica", style="bold")
        table.add_column("Gap %", justify="right")
        table.add_column("Media Uomini", justify="right")
        table.add_column("Media Donne", justify="right")
        table.add_column("N. Uomini", justify="right")
        table.add_column("N. Donne", justify="right")

        table.add_row(
            "Mean Gap (media)",
            self._colored_gap(mean.gap_pct),
            f"EUR {mean.male_avg:,.0f}",
            f"EUR {mean.female_avg:,.0f}",
            str(mean.male_count),
            str(mean.female_count),
        )
        table.add_row(
            "Median Gap (mediana)",
            self._colored_gap(median.gap_pct),
            f"EUR {median.male_avg:,.0f}",
            f"EUR {median.female_avg:,.0f}",
            str(median.male_count),
            str(median.female_count),
        )

        console.print()
        console.print(table)

    def _print_category_gaps(self) -> None:
        """
        Stampa il gap per ogni categoria (dipartimento + livello).

        Le categorie con gap > 5% sono evidenziate in rosso.
        """
        gaps = self.result.category_gaps
        if not gaps:
            console.print("\n[dim]Gap per categoria non disponibile "
                          "(colonne department/level mancanti)[/dim]")
            return

        table = Table(title="Gap per Categoria (Dipartimento + Livello)")
        table.add_column("Dipartimento", style="bold")
        table.add_column("Livello")
        table.add_column("Gap %", justify="right")
        table.add_column("Media M", justify="right")
        table.add_column("Media F", justify="right")
        table.add_column("N.M", justify="right")
        table.add_column("N.F", justify="right")
        table.add_column("Status", justify="center")

        for cat in gaps:
            status = "[red bold]ALERT[/red bold]" if cat.is_significant else "[green]OK[/green]"
            table.add_row(
                cat.department,
                cat.level,
                self._colored_gap(cat.gap_pct),
                f"EUR {cat.male_avg:,.0f}",
                f"EUR {cat.female_avg:,.0f}",
                str(cat.male_count),
                str(cat.female_count),
                status,
            )

        console.print()
        console.print(table)

    def _print_quartiles(self) -> None:
        """
        Stampa la distribuzione di genere nei quartili retributivi.

        Mostra una barra visuale per rendere immediato lo squilibrio.
        """
        quartiles = self.result.quartiles
        if not quartiles:
            return

        table = Table(title="Distribuzione per Quartili Retributivi")
        table.add_column("Quartile", style="bold", justify="center")
        table.add_column("Range Stipendio", justify="right")
        table.add_column("Totale", justify="right")
        table.add_column("% Uomini", justify="right")
        table.add_column("% Donne", justify="right")
        table.add_column("Distribuzione", justify="left")

        labels = {1: "Q1 (basso)", 2: "Q2", 3: "Q3", 4: "Q4 (alto)"}

        for q in quartiles:
            # Barra visuale: ogni carattere = ~5%
            bar_m = "[blue]" + "#" * int(q.male_pct / 5) + "[/blue]"
            bar_f = "[magenta]" + "#" * int(q.female_pct / 5) + "[/magenta]"
            bar = f"M {bar_m} | F {bar_f}"

            table.add_row(
                labels.get(q.quartile, f"Q{q.quartile}"),
                f"EUR {q.min_salary:,.0f} - {q.max_salary:,.0f}",
                str(q.total),
                f"{q.male_pct}%",
                f"{q.female_pct}%",
                bar,
            )

        console.print()
        console.print(table)

    def _print_bonus_gap(self) -> None:
        """Stampa il gap nei bonus."""
        bonus = self.result.bonus_gap
        if bonus is None:
            console.print("\n[dim]Analisi bonus non disponibile "
                          "(colonna 'bonus' mancante)[/dim]")
            return

        table = Table(title="Gap nei Bonus")
        table.add_column("Metrica", style="bold")
        table.add_column("Valore", justify="right")

        table.add_row("Bonus Gap", self._colored_gap(bonus.gap_pct))
        table.add_row("Media Bonus Uomini", f"EUR {bonus.male_avg:,.0f}")
        table.add_row("Media Bonus Donne", f"EUR {bonus.female_avg:,.0f}")
        table.add_row("N. Uomini con bonus", str(bonus.male_count))
        table.add_row("N. Donne con bonus", str(bonus.female_count))

        console.print()
        console.print(table)

    def _print_compliance_summary(self) -> None:
        """
        Stampa il riepilogo di compliance con la Direttiva EU.

        Questo è il "verdetto finale": l'azienda è compliant o no?
        """
        is_ok = self.result.is_compliant
        non_compliant = self.result.non_compliant_categories

        if is_ok:
            panel_style = "green"
            status_text = Text("COMPLIANT", style="bold green")
            detail = Text(
                "Nessuna categoria presenta un gap superiore al 5%.\n"
                "L'azienda soddisfa i requisiti della Direttiva EU 2023/970.",
                style="green"
            )
        else:
            panel_style = "red"
            status_text = Text("NON COMPLIANT", style="bold red")

            lines = [
                f"{len(non_compliant)} categorie presentano un gap > 5%:\n"
            ]
            for cat in non_compliant:
                lines.append(f"  - {cat.department} {cat.level}: {cat.gap_pct:+.1f}%")
            lines.append(
                "\nArt. 10 Direttiva EU 2023/970: l'azienda deve condurre una "
                "valutazione retributiva congiunta e adottare misure correttive."
            )
            detail = Text("\n".join(lines), style="yellow")

        content = Text.assemble(
            Text("Stato: "), status_text, Text("\n\n"), detail
        )

        console.print()
        console.print(Panel(
            content,
            title="Verifica Compliance EU 2023/970",
            border_style=panel_style,
            padding=(1, 2),
        ))
        console.print()

    # =========================================================================
    # UTILITY
    # =========================================================================

    @staticmethod
    def _colored_gap(gap_pct: float) -> str:
        """
        Restituisce il gap formattato con colore in base alla gravità.

        - Verde: |gap| <= 5%
        - Giallo: |gap| tra 5% e 10%
        - Rosso: |gap| > 10%
        """
        abs_gap = abs(gap_pct)
        if abs_gap <= 5.0:
            color = "green"
        elif abs_gap <= 10.0:
            color = "yellow"
        else:
            color = "red bold"

        return f"[{color}]{gap_pct:+.1f}%[/{color}]"
