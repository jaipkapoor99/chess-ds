"""Command-line interface for chess-ds sharding and resumable evaluation."""

import argparse
from pathlib import Path

from chess_ds.evaluator import ResumableBenchmarkRunner
from chess_ds.fetcher import SHARDS_DIR, LichessFetcher
from chess_ds.telemetry import TelemetryDashboard


def main():
    parser = argparse.ArgumentParser(
        description="Chess-DS High-Performance Engine Benchmark Platform"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch/Stream command
    fetch_parser = subparsers.add_parser(
        "fetch", help="Stream and shard ultra-hard puzzles live from official Lichess database"
    )
    fetch_parser.add_argument(
        "--min-rating", type=int, default=2500, help="Minimum puzzle rating (default: 2500)"
    )
    fetch_parser.add_argument(
        "--total", type=int, default=5000, help="Total puzzles to stream (default: 5000)"
    )
    fetch_parser.add_argument(
        "--shard-size", type=int, default=1000, help="Puzzles per Parquet shard (default: 1000)"
    )
    fetch_parser.add_argument(
        "--popularity", type=int, default=80, help="Minimum popularity rating (default: 80)"
    )

    # Run command
    run_parser = subparsers.add_parser("eval", help="Run resumable benchmark across shards")
    run_parser.add_argument(
        "--total", type=int, default=5000, help="Total target positions to evaluate (default: 5000)"
    )
    run_parser.add_argument(
        "--movetime", type=int, default=500, help="Time per position in ms (default: 500)"
    )
    run_parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of engines to run concurrently (default: 1)",
    )
    run_parser.add_argument(
        "--engines",
        nargs="+",
        default=["Lc0 v0.32.1", "Stockfish 18", "Reckless 0.9.0"],
        help="Engines to test",
    )
    run_parser.add_argument(
        "--wandb",
        action="store_true",
        help="Enable live Weights & Biases telemetry logging",
    )
    run_parser.add_argument(
        "--wandb-project",
        type=str,
        default="chess-ds",
        help="Weights & Biases project name (default: chess-ds)",
    )
    run_parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force a fresh benchmark run from scratch (ignores previous completed shards)",
    )
    run_parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run identifier / timestamp (default: auto-generated timestamp)",
    )

    # Summary command
    subparsers.add_parser(
        "summary", help="Query and display DuckDB analytics across completed results"
    )

    # Export CSV from Query command
    export_parser = subparsers.add_parser(
        "export-csv", help="Export DuckDB query results over Parquet tables directly to CSV"
    )
    export_parser.add_argument(
        "--query",
        type=str,
        default="SELECT engine, COUNT(*) as total_puzzles, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as solved, ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)*100, 2) as accuracy_pct, ROUND(AVG(nps), 0) as avg_nps, ROUND(AVG(depth), 1) as avg_depth, ROUND(AVG(elapsed_seconds), 3) as avg_sec_per_pos FROM read_parquet('data/results/*.parquet') GROUP BY engine ORDER BY accuracy_pct DESC",
        help="SQL query to execute against DuckDB",
    )
    export_parser.add_argument(
        "--output",
        type=str,
        default="data/results/query_export.csv",
        help="Output CSV file path",
    )

    args = parser.parse_args()

    if args.command == "fetch":
        TelemetryDashboard.print_banner(
            "chess-ds Ingestion Pipeline", "Streaming from database.lichess.org"
        )
        LichessFetcher.build_live_parquet_shards(
            min_rating=args.min_rating,
            popularity_min=args.popularity,
            total_puzzles=args.total,
            shard_size=args.shard_size,
        )

    elif args.command == "eval":
        TelemetryDashboard.print_banner(
            "chess-ds Multi-Engine Benchmark",
            f"Search: {args.movetime}ms/pos | Concurrency: {args.concurrency}",
        )
        shards = sorted(SHARDS_DIR.glob("*.parquet"))
        if not shards:
            print(
                "No shards found. Streaming fresh ultra-hard puzzles live from official Lichess repository..."
            )
            shards = LichessFetcher.build_live_parquet_shards(
                min_rating=2500, total_puzzles=args.total, shard_size=1000
            )

        runner = ResumableBenchmarkRunner(
            movetime_ms=args.movetime,
            run_id=args.run_id,
            use_wandb=args.wandb,
            wandb_project=args.wandb_project,
            force_fresh=args.fresh,
        )
        runner.run_suite(
            shards,
            engines=args.engines,
            concurrency=args.concurrency,
            total_limit=args.total,
        )

    elif args.command == "summary":
        TelemetryDashboard.print_banner("chess-ds Analytics Dashboard", "Zero-Copy Parquet Rollup")
        TelemetryDashboard.render_results_summary()

    elif args.command == "export-csv":
        TelemetryDashboard.print_banner("chess-ds Query Exporter", f"Exporting to {args.output}")
        ResumableBenchmarkRunner.export_csv_from_query(args.query, Path(args.output))


if __name__ == "__main__":
    main()
