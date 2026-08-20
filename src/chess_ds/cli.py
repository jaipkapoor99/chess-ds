"""Command-line interface for chess-ds sharding and resumable evaluation."""

import argparse

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
        "--movetime", type=int, default=500, help="Time per position in ms (default: 500)"
    )
    run_parser.add_argument(
        "--engines",
        nargs="+",
        default=["Lc0 v0.32.1", "Reckless 0.9.0", "Stockfish 18"],
        help="Engines to test",
    )

    # Summary command
    subparsers.add_parser(
        "summary", help="Query and display DuckDB analytics across completed results"
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
            "chess-ds Multi-Engine Benchmark", f"Search Budget: {args.movetime}ms/pos"
        )
        shards = sorted(SHARDS_DIR.glob("*.parquet"))
        if not shards:
            print(
                "No shards found. Streaming fresh ultra-hard puzzles live from official Lichess repository..."
            )
            shards = LichessFetcher.build_live_parquet_shards(
                min_rating=2500, total_puzzles=5000, shard_size=1000
            )

        runner = ResumableBenchmarkRunner(movetime_ms=args.movetime)
        runner.run_suite(shards, engines=args.engines)

    elif args.command == "summary":
        TelemetryDashboard.print_banner("chess-ds Analytics Dashboard", "Zero-Copy Parquet Rollup")
        TelemetryDashboard.render_results_summary()


if __name__ == "__main__":
    main()
