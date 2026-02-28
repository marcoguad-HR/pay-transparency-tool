"""
CLI Interface — Dispatcher dei comandi verso i moduli del progetto.

Collega il parsing degli argomenti (main.py) alle funzionalità di business:
- ingest  → src.rag.ingestion.DirectiveIngestion
- query   → src.rag.generator.RAGGenerator
- analyze → src.analysis (DataLoader + GapCalculator + PayGapReport)
- agent   → src.agent.router.PayTransparencyRouter

Principi di design:
- Lazy import: i moduli pesanti vengono importati solo quando servono,
  così "python main.py --help" è istantaneo.
- rich Console: output coerente con il report module (src/analysis/report.py).
- Error handling: messaggi user-friendly per errori comuni.
"""

from rich.console import Console
from rich.panel import Panel

from src.utils.logger import get_logger
from src.utils.rate_limiter import RateLimitError

logger = get_logger("cli")
console = Console()


class CLI:
    """Dispatcher dei comandi CLI verso i moduli di business."""

    def dispatch(self, args):
        """Ruota gli argomenti parsed al handler corretto."""
        handlers = {
            "ingest": self._handle_ingest,
            "query": self._handle_query,
            "analyze": self._handle_analyze,
            "agent": self._handle_agent,
        }

        handler = handlers.get(args.command)
        if handler is None:
            console.print(f"[red]Comando sconosciuto: {args.command}[/red]")
            return

        try:
            handler(args)
        except KeyboardInterrupt:
            console.print("\n[dim]Interrotto dall'utente.[/dim]")
        except RateLimitError as e:
            console.print(f"[yellow bold]Rate Limit:[/yellow bold] {e}")
            console.print("[dim]Suggerimento: attendi qualche minuto prima di riprovare.[/dim]")
        except Exception as e:
            console.print(f"[red bold]Errore:[/red bold] {e}")
            logger.error(f"Errore nel comando '{args.command}': {e}", exc_info=True)

    def _handle_ingest(self, args):
        """Ingestione PDF → vector database."""
        from src.rag.ingestion import DirectiveIngestion

        ingestion = DirectiveIngestion()

        if args.reset:
            ingestion.reset()
            console.print("[yellow]Vector DB resettato.[/yellow]")

        console.print(f"[dim]Ingestion di {args.pdf_path}...[/dim]")
        n_chunks = ingestion.ingest(args.pdf_path)
        console.print(f"[green]Ingestion completata: {n_chunks} chunk creati.[/green]")

    def _handle_query(self, args):
        """Domanda RAG sulla direttiva."""
        from src.rag.generator import RAGGenerator

        generator = RAGGenerator()
        response = generator.generate(args.question, verify=args.verify)

        console.print()
        console.print(Panel(response.answer, title="Risposta", border_style="blue"))
        console.print(f"[dim]Confidenza: {response.confidence:.0%}[/dim]")

        if response.verified is not None:
            if response.verified:
                console.print("[green]Anti-allucinazione: Verificata[/green]")
            else:
                console.print("[red]Anti-allucinazione: Non verificata[/red]")
                if response.verification_reasoning:
                    console.print(f"[dim]Motivo: {response.verification_reasoning}[/dim]")

    def _handle_analyze(self, args):
        """Analisi gender pay gap."""
        from src.analysis.data_loader import PayDataLoader
        from src.analysis.gap_calculator import GapCalculator
        from src.analysis.report import PayGapReport

        loader = PayDataLoader()
        load_result = loader.load(args.file_path)

        # Mostra eventuali warning di qualità dati
        for warning in load_result.warnings:
            console.print(f"[yellow]Avviso: {warning}[/yellow]")

        calculator = GapCalculator(load_result.df)

        if args.analysis_type == "full":
            result = calculator.full_analysis()
            report = PayGapReport(result)
            report.print_full_report()
        else:
            # Per analisi parziali, usa le funzioni di formattazione del router
            from src.agent.router import (
                _format_overall,
                _format_categories,
                _format_quartiles,
                _format_bonus,
                _format_compliance,
            )

            formatters = {
                "overall": lambda: _format_overall(calculator, load_result),
                "category": lambda: _format_categories(calculator),
                "quartiles": lambda: _format_quartiles(calculator),
                "bonus": lambda: _format_bonus(calculator),
                "compliance": lambda: _format_compliance(calculator),
            }

            output = formatters[args.analysis_type]()
            console.print()
            console.print(output)

    def _handle_agent(self, args):
        """Agent interattivo o singola domanda."""
        from src.agent.router import PayTransparencyRouter

        router = PayTransparencyRouter()

        if args.question:
            answer = router.ask(args.question)
            console.print()
            console.print(Panel(answer, title="Agent", border_style="green"))
        else:
            self._interactive_agent(router)

    def _interactive_agent(self, router):
        """Modalità REPL interattiva con l'agent."""
        console.print()
        console.print(Panel(
            "Modalità interattiva. Scrivi [bold]exit[/bold] per uscire.\n"
            "Puoi fare domande sulla Direttiva EU 2023/970 o sui dati retributivi.",
            title="Pay Transparency Agent",
            border_style="green",
        ))

        while True:
            try:
                question = console.input("\n[bold blue]> [/bold blue]")
                if question.strip().lower() in ("exit", "quit", "esci"):
                    break
                if not question.strip():
                    continue

                console.print("[dim]Elaborazione...[/dim]")
                answer = router.ask(question)
                console.print(f"\n{answer}")

            except KeyboardInterrupt:
                break
            except RateLimitError as e:
                console.print(f"[yellow]Rate Limit: {e}[/yellow]")
                console.print("[dim]Attendi qualche minuto prima di riprovare.[/dim]")
            except Exception as e:
                console.print(f"[red]Errore: {e}[/red]")
                logger.error(f"Errore nell'agent interattivo: {e}", exc_info=True)

        console.print("\n[dim]Arrivederci![/dim]")
