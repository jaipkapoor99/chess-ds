"""Dedicated Rich Telemetry and Analytical Dashboard for chess-ds."""

from pathlib import Path

import duckdb
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT_DIR / "data" / "results"
console = Console()


class WandbLogger:
    """Manages Weights & Biases experiment tracking, metric logging, and table sync."""

    def __init__(
        self,
        project_name: str = "chess-ds",
        run_name: str | None = None,
        config: dict | None = None,
        offline: bool = False,
    ):
        self.enabled = False
        try:
            import wandb

            mode = "offline" if offline else "online"
            self.run = wandb.init(
                project=project_name,
                name=run_name,
                config=config or {},
                mode=mode,
            )
            self.enabled = True
            console.print(
                f"[bold cyan]Weights & Biases initialized[/bold cyan] in [bold green]{mode}[/bold green] mode."
            )
        except Exception as e:
            console.print(f"[dim yellow]WandB init notice ({e})[/dim yellow]")

    def log_position_metrics(
        self,
        engine: str,
        index: int,
        is_correct: bool,
        running_accuracy: float,
        depth: int,
        nps: float,
        elapsed: float,
        rating: int,
    ) -> None:
        """Logs real-time single-position metrics to WandB."""
        if not self.enabled:
            return
        import wandb

        wandb.log(
            {
                f"{engine}/running_accuracy_pct": running_accuracy,
                f"{engine}/depth": depth,
                f"{engine}/nps": nps,
                f"{engine}/elapsed_seconds": elapsed,
                f"{engine}/puzzle_rating": rating,
                f"{engine}/solved_binary": 1 if is_correct else 0,
                "global_position_step": index,
            }
        )

    def finish(self) -> None:
        """Closes WandB run session."""
        if self.enabled:
            import wandb

            wandb.finish()


class TelemetryDashboard:
    """Renders formatted tables, progress reports, and telemetry."""

    @staticmethod
    def print_banner(title: str, subtitle: str | None = None):
        """Prints a styled Rich header banner."""
        content = Text(title, style="bold cyan")
        if subtitle:
            content.append(f"\n{subtitle}", style="dim white")
        console.print(Panel(content, box=ROUNDED, border_style="bright_blue", expand=False))

    @staticmethod
    def print_engine_card(engine_name: str, config: dict):
        """Prints engine specifications in a styled panel."""
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_column("Key", style="bold yellow")
        t.add_column("Value", style="green")

        for k, v in config.items():
            t.add_row(k.capitalize(), str(v))

        console.print(
            Panel(
                t,
                title=f"[bold white]{engine_name}[/bold white]",
                border_style="magenta",
                expand=False,
            )
        )

    @classmethod
    def render_results_summary(cls, parquet_glob: str = "data/results/*.parquet"):
        """Queries completed evaluations with DuckDB and displays Rich summary table."""
        parquet_files = list(RESULTS_DIR.glob("*.parquet"))
        if not parquet_files:
            console.print(
                "[bold red]No evaluation Parquet files found in data/results/.[/bold red]"
            )
            return

        con = duckdb.connect()
        query = f"""
        SELECT
            engine,
            COUNT(*) as total_puzzles,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as solved,
            ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) * 100.0, 2) as accuracy_pct,
            ROUND(AVG(nps), 0) as avg_nps,
            ROUND(AVG(depth), 1) as avg_depth,
            ROUND(AVG(elapsed_seconds), 3) as avg_sec,
            ROUND(SUM(elapsed_seconds), 1) as total_sec
        FROM read_parquet('{parquet_glob}')
        GROUP BY engine
        ORDER BY accuracy_pct DESC, avg_nps DESC
        """
        try:
            df = con.execute(query).pl()
        except Exception as e:
            console.print(f"[bold red]DuckDB query error:[/bold red] {e}")
            return

        table = Table(
            title="[bold green]Engine Evaluation & Telemetry Rollup[/bold green]",
            box=ROUNDED,
            header_style="bold bright_white on blue",
            border_style="bright_blue",
        )

        table.add_column("Engine", style="bold cyan", no_wrap=True)
        table.add_column("Solved / Total", justify="center", style="bold white")
        table.add_column("Accuracy", justify="right", style="bold green")
        table.add_column("Avg NPS (Speed)", justify="right", style="bold yellow")
        table.add_column("Avg Depth", justify="right", style="magenta")
        table.add_column("Avg Time/Pos", justify="right", style="dim white")
        table.add_column("Total Time", justify="right", style="cyan")

        for row in df.iter_rows(named=True):
            acc_str = f"{row['accuracy_pct']:.2f}%"
            acc_style = "bold green" if row["accuracy_pct"] >= 99.0 else "bold yellow"

            table.add_row(
                row["engine"],
                f"{row['solved']:,} / {row['total_puzzles']:,}",
                Text(acc_str, style=acc_style),
                f"{row['avg_nps']:,.0f}",
                f"{row['avg_depth']:.1f}",
                f"{row['avg_sec']:.3f}s",
                f"{row['total_sec']:.1f}s",
            )

        console.print(table)


if __name__ == "__main__":
    TelemetryDashboard.print_banner("chess-ds Telemetry Suite", "Zero-Copy Analytics Dashboard")
    TelemetryDashboard.render_results_summary()
