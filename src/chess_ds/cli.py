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
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable live Weights & Biases telemetry logging (default: enabled)",
    )
    run_parser.add_argument(
        "--wandb-project",
        type=str,
        default="chess-ds",
        help="Weights & Biases project name (default: chess-ds)",
    )
    run_parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume an interrupted run by providing its Run ID (recovers all parameters automatically)",
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

    # Export Enriched PGN command
    export_pgn_parser = subparsers.add_parser(
        "export-pgn",
        help="Export and reconstruct annotated PGN files directly from database match tables",
    )
    export_pgn_parser.add_argument(
        "--match-id",
        type=str,
        default=None,
        help="Match ID to export from Parquet database (e.g. match_20260820_220029)",
    )
    export_pgn_parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input raw match PGN file path (alternative to --match-id)",
    )
    export_pgn_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output annotated PGN file path (defaults to data/results/matches/<match_id>.pgn)",
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
        runner = ResumableBenchmarkRunner(
            movetime_ms=args.movetime,
            run_id=args.resume,
            use_wandb=args.wandb,
            wandb_project=args.wandb_project,
            total_puzzles=args.total,
            concurrency=args.concurrency,
            engines=args.engines,
        )

        TelemetryDashboard.print_banner(
            f"chess-ds Benchmark: {runner.run_id}",
            f"Search: {runner.movetime_ms}ms/pos | Total: {runner.total_puzzles} | Concurrency: {runner.concurrency}",
        )

        from chess_ds.fetcher import DATA_DIR
        shards = sorted(DATA_DIR.glob("lichess_shard_*.parquet"))
        if not shards:
            print("No puzzle shards found. Run `chess_ds fetch` first.")
            return

        runner.run_suite(
            shards,
            engine_names=runner.engines,
            concurrency=runner.concurrency,
            total_limit=runner.total_puzzles,
        )

    elif args.command == "summary":
        TelemetryDashboard.print_banner("chess-ds Analytics Dashboard", "Zero-Copy Parquet Rollup")
        runner = ResumableBenchmarkRunner()
        runner.generate_analytics_summary()

    elif args.command == "export-csv":
        out_path = Path(args.output)
        TelemetryDashboard.print_banner("chess-ds Query Exporter", f"Exporting to {args.output}")
        ResumableBenchmarkRunner.export_csv_from_query(args.query, Path(args.output))

    elif args.command == "export-pgn":
        from chess_ds.match_ingest import enrich_and_export_pgn, export_pgn_from_db

        if args.match_id:
            out_p = (
                Path(args.output)
                if args.output
                else Path(f"data/results/matches/{args.match_id}.pgn")
            )
            res_p = export_pgn_from_db(args.match_id, out_p)
            print(f"✓ Reconstructed and exported PGN from database to: {res_p}")
        elif args.input:
            in_p = Path(args.input)
            out_p = Path(args.output) if args.output else None
            res_p = enrich_and_export_pgn(in_p, out_p)
            print(f"✓ Enriched PGN with engine telemetry exported to: {res_p}")
        else:
            print("Please specify either --match-id <id> or --input <pgn_path>.")


if __name__ == "__main__":
    main()
