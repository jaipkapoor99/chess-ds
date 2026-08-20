"""Distributed and Resumable Multi-Engine Benchmark Pipeline.
Features:
- Checkpointing & Automatic Resume on interruption.
- Rich tqdm progress bars with live accuracy, speed (NPS), and depth telemetry.
- Parquet shard streaming and DuckDB analytical rollups.
"""

import json
import time
from pathlib import Path

import duckdb
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

from chess_ds.engines import EngineSession

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
SHARDS_DIR = DATA_DIR / "shards"
RESULTS_DIR = DATA_DIR / "results"
CHECKPOINTS_DIR = DATA_DIR / "checkpoints"


class ResumableBenchmarkRunner:
    """Orchestrates multi-engine evaluation across Parquet shards with run_id metadata checkpointing."""

    def __init__(
        self,
        movetime_ms: int = 500,
        run_id: str | None = None,
        use_wandb: bool = False,
        wandb_project: str = "chess-ds",
        total_puzzles: int = 5000,
        concurrency: int = 1,
        engines: list[str] | None = None,
    ):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

        self.run_id = run_id or time.strftime("run_%Y%m%d_%H%M%S")
        self.meta_path = CHECKPOINTS_DIR / f"{self.run_id}_meta.json"

        # Check if we are resuming an existing run manifest
        if self.meta_path.exists():
            try:
                with open(self.meta_path) as f:
                    meta = json.load(f)
                self.movetime_ms = meta.get("movetime_ms", movetime_ms)
                self.total_puzzles = meta.get("total_puzzles", total_puzzles)
                self.concurrency = meta.get("concurrency", concurrency)
                self.engines = meta.get(
                    "engines", engines or ["Lc0 v0.32.1", "Stockfish 18", "Reckless 0.9.0"]
                )
                self.use_wandb = meta.get("use_wandb", use_wandb)
                self.wandb_project = meta.get("wandb_project", wandb_project)
                print(f"↺ [RESUME] Recovered metadata for Run ID: {self.run_id}")
            except Exception:
                self.movetime_ms = movetime_ms
                self.total_puzzles = total_puzzles
                self.concurrency = concurrency
                self.engines = engines or ["Lc0 v0.32.1", "Stockfish 18", "Reckless 0.9.0"]
                self.use_wandb = use_wandb
                self.wandb_project = wandb_project
        else:
            self.movetime_ms = movetime_ms
            self.total_puzzles = total_puzzles
            self.concurrency = concurrency
            self.engines = engines or ["Lc0 v0.32.1", "Stockfish 18", "Reckless 0.9.0"]
            self.use_wandb = use_wandb
            self.wandb_project = wandb_project

            # Save initial manifest
            manifest = {
                "run_id": self.run_id,
                "movetime_ms": self.movetime_ms,
                "total_puzzles": self.total_puzzles,
                "concurrency": self.concurrency,
                "engines": self.engines,
                "use_wandb": self.use_wandb,
                "wandb_project": self.wandb_project,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            with open(self.meta_path, "w") as f:
                json.dump(manifest, f, indent=2)

        self.wandb_logger = None
        if self.use_wandb:
            from chess_ds.telemetry import WandbLogger

            self.wandb_logger = WandbLogger(
                project_name=self.wandb_project, run_name=f"benchmark_{self.run_id}"
            )

    def get_checkpoint_path(self, engine_name: str, shard_path: Path) -> Path:
        safe_name = engine_name.lower().replace(" ", "_").replace(".", "_")
        return CHECKPOINTS_DIR / f"{self.run_id}_{safe_name}_{shard_path.stem}.json"

    def get_result_shard_path(self, engine_name: str, shard_path: Path) -> Path:
        safe_name = engine_name.lower().replace(" ", "_").replace(".", "_")
        return RESULTS_DIR / f"eval_{self.run_id}_{safe_name}_{shard_path.stem}.parquet"

    def evaluate_shard_with_engine(
        self,
        engine_name: str,
        shard_path: Path,
        max_puzzles: int | None = None,
    ) -> dict:
        """Evaluates a parquet shard with state resumption keyed by self.run_id."""
        result_path = self.get_result_shard_path(engine_name, shard_path)
        ckpt_path = self.get_checkpoint_path(engine_name, shard_path)

        # Check if entire shard was already evaluated for this run_id
        if result_path.exists():
            print(
                f"[{engine_name}] Shard {shard_path.name} already completed in {result_path.name}. Skipping."
            )
            return {"status": "already_done", "path": str(result_path)}

        # Load input shard table
        df = pl.read_parquet(shard_path)
        if max_puzzles is not None and max_puzzles < len(df):
            df = df.slice(0, max_puzzles)

        total_puzzles = len(df)

        # Check resume checkpoint
        evaluated_rows: list[dict] = []
        start_idx = 0

        if ckpt_path.exists():
            try:
                with open(ckpt_path) as f:
                    ckpt = json.load(f)
                    start_idx = ckpt.get("last_index", 0)
                    evaluated_rows = ckpt.get("results", [])
                print(
                    f"[{engine_name}] ↺ Resuming {shard_path.name} from position {start_idx}/{total_puzzles}..."
                )
            except (json.JSONDecodeError, OSError, KeyError):
                start_idx = 0
                evaluated_rows = []

        session = EngineSession(engine_name)
        solved_count = sum(1 for r in evaluated_rows if r.get("is_correct", False))

        pbar = tqdm(
            total=total_puzzles,
            initial=start_idx,
            desc=f"{engine_name} ({shard_path.stem})",
            unit="pos",
            dynamic_ncols=True,
        )

        rows_iter = df.iter_rows(named=True)
        for _ in range(start_idx):
            next(rows_iter, None)

        for i, row in enumerate(rows_iter, start=start_idx):
            fen = row["fen"]
            solution = row["solution"]
            puzzle_id = row["puzzle_id"]
            rating = row["rating"]

            bm, depth, nps, elapsed = session.evaluate_fen(fen, movetime_ms=self.movetime_ms)
            is_correct = bm == solution
            if is_correct:
                solved_count += 1

            record = {
                "run_id": self.run_id,
                "puzzle_id": puzzle_id,
                "fen": fen,
                "solution": solution,
                "engine_move": bm,
                "is_correct": is_correct,
                "depth": depth,
                "nps": nps,
                "elapsed_seconds": elapsed,
                "rating": rating,
                "engine": engine_name,
                "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            evaluated_rows.append(record)

            acc = (solved_count / (i + 1)) * 100.0
            pbar.set_postfix(
                {
                    "Acc": f"{acc:.1f}%",
                    "NPS": f"{nps:,.0f}" if nps > 0 else "N/A",
                    "Depth": depth,
                    "Move": bm,
                }
            )
            pbar.update(1)

            if self.wandb_logger:
                self.wandb_logger.log_position_metrics(
                    engine=engine_name,
                    index=i + 1,
                    is_correct=is_correct,
                    running_accuracy=acc,
                    depth=depth,
                    nps=nps,
                    elapsed=elapsed,
                    rating=rating,
                )

            # Checkpoint every 50 positions
            if (i + 1) % 50 == 0 or (i + 1) == total_puzzles:
                with open(ckpt_path, "w") as f:
                    json.dump(
                        {
                            "run_id": self.run_id,
                            "last_index": i + 1,
                            "results": evaluated_rows,
                        },
                        f,
                    )

        pbar.close()
        session.close()

        # Write final Parquet result table
        res_table = pa.Table.from_pylist(evaluated_rows)
        pq.write_table(res_table, result_path, compression="zstd")

        # Remove temporary checkpoint on successful completion
        if ckpt_path.exists():
            ckpt_path.unlink()

        return {
            "status": "completed",
            "shard": shard_path.name,
            "engine": engine_name,
            "total": total_puzzles,
            "solved": solved_count,
            "accuracy": (solved_count / total_puzzles) * 100.0,
            "result_path": str(result_path),
        }

    def run_suite(
        self,
        shards: list[Path],
        engines: list[str] | None = None,
        concurrency: int = 1,
        total_limit: int | None = None,
    ) -> None:
        """Executes benchmark suite across shards and engines with dynamic concurrency and exact position limits."""
        if engines is None:
            engines = ["Lc0 v0.32.1", "Stockfish 18", "Reckless 0.9.0"]

        print("\n=================================================================")
        print("  STARTING MULTI-ENGINE RESUMABLE BENCHMARK SUITE")
        limit_str = f"{total_limit:,} Positions" if total_limit else "All Available"
        print(f"  Target: {limit_str} | Engines: {len(engines)} | Concurrency: {concurrency}")
        print("=================================================================\n")

        from concurrent.futures import ThreadPoolExecutor

        def run_for_engine(engine_name: str) -> None:
            remaining = total_limit
            for shard in shards:
                if remaining is not None and remaining <= 0:
                    break

                # Check shard size
                shard_len = len(pl.read_parquet(shard))
                eval_count = min(shard_len, remaining) if remaining is not None else shard_len
                self.evaluate_shard_with_engine(engine_name, shard, max_puzzles=eval_count)
                if remaining is not None:
                    remaining -= eval_count

        if concurrency > 1:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                list(executor.map(run_for_engine, engines))
        else:
            for engine in engines:
                run_for_engine(engine)

        if self.wandb_logger:
            self.wandb_logger.finish()

        self.generate_analytics_summary()

    def generate_analytics_summary(self) -> None:
        """Runs DuckDB analytical queries across all result parquet files."""
        result_files = list(RESULTS_DIR.glob("eval_*.parquet"))
        if not result_files:
            print("No evaluation results found.")
            return

        con = duckdb.connect()
        query = """
        SELECT
            engine,
            COUNT(*) as total_puzzles,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as solved,
            ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) * 100.0, 2) as accuracy_pct,
            ROUND(AVG(nps), 0) as avg_nps,
            ROUND(AVG(depth), 1) as avg_depth,
            ROUND(AVG(elapsed), 3) as avg_sec_per_pos,
            ROUND(AVG(rating), 0) as avg_puzzle_rating
        FROM read_parquet('data/results/eval_*.parquet')
        GROUP BY engine
        ORDER BY accuracy_pct DESC, avg_nps DESC
        """
        df_summary = con.execute(query).pl()

        print("\n" + "=" * 110)
        print("                         CONSOLIDATED ENGINE ANALYTICS SUMMARY")
        print("=" * 110)
        print(df_summary)
        print("=" * 110)

    @classmethod
    def export_csv_from_query(
        cls,
        sql_query: str,
        output_csv_path: Path,
    ) -> None:
        """Executes a DuckDB SQL analytical query over Parquet files and exports the result to CSV."""
        con = duckdb.connect()
        try:
            con.execute(f"COPY ({sql_query}) TO '{output_csv_path}' (HEADER, DELIMITER ',')")
            print(f"✓ DuckDB query result exported to: {output_csv_path}")
        except Exception as e:
            print(f"Query export error: {e}")
        print("=" * 110)
