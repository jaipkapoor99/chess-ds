"""Command-line interface for chess-ds sharding and resumable evaluation."""

import argparse

from chess_ds.evaluator import ResumableBenchmarkRunner
from chess_ds.sharder import SHARDS_DIR, build_puzzle_shards


def main():
    parser = argparse.ArgumentParser(
        description="Chess-DS High-Performance Engine Benchmark Platform"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shard command
    shard_parser = subparsers.add_parser(
        "shard", help="Extract and shard ultra-hard puzzles into Parquet format"
    )
    shard_parser.add_argument(
        "--min-rating", type=int, default=2500, help="Minimum puzzle rating (default: 2500)"
    )
    shard_parser.add_argument(
        "--total", type=int, default=5000, help="Total target puzzle count (default: 5000)"
    )
    shard_parser.add_argument(
        "--shard-size", type=int, default=1000, help="Puzzles per Parquet shard (default: 1000)"
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

    if args.command == "shard":
        build_puzzle_shards(
            min_rating=args.min_rating, total_target=args.total, shard_size=args.shard_size
        )

    elif args.command == "eval":
        shards = sorted(SHARDS_DIR.glob("shard_*.parquet"))
        if not shards:
            print("No shards found. Generating shards first...")
            shards = build_puzzle_shards(min_rating=2500, total_target=5000, shard_size=1000)

        runner = ResumableBenchmarkRunner(movetime_ms=args.movetime)
        runner.run_suite(shards, engines=args.engines)

    elif args.command == "summary":
        runner = ResumableBenchmarkRunner()
        runner.generate_analytics_summary()


if __name__ == "__main__":
    main()
