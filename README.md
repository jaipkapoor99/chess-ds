# ♟️ `chess-ds`: Pedagogical Chess Data Science & Engine Analytics Platform

> [!NOTE]
> **Pedagogical Purpose**: This repository is designed as an educational, pedagogical research platform demonstrating modern chess data science, high-performance engine benchmarking, neural network vs. alpha-beta search paradigms, and distributed data pipelines.

> [!IMPORTANT]
> **Benchmarking Scripts Note**: Exact one-size-fits-all benchmarking scripts are deliberately not hardcoded because evaluation workflows vary significantly based on hardware topography (GPU tensor batching vs. multi-threaded CPU AVX-512 allocations), time controls, endgame tablebase lookups, and concurrency constraints. Instead, modular orchestrators and CLI templates are provided.

______________________________________________________________________

## 1. Core Architecture & Concepts Demonstrated

1. **Neural MCTS vs. Alpha-Beta Evaluation**:

   - **Leela Chess Zero ([`Lc0`](https://github.com/LeelaChessZero/lc0))**: GPU-accelerated Monte Carlo Tree Search (MCTS) utilizing deep Policy-Value Transformer neural networks (`BT4-332.pb`) running on Tensor Cores.
   - **Stockfish ([`Stockfish`](https://github.com/official-stockfish/Stockfish))**: Highly optimized CPU Alpha-Beta search engine powered by AVX-512 NNUE evaluation.
   - **Reckless ([`Reckless`](https://github.com/lucasart/reckless))**: High-performance open-source UCI chess engine featuring advanced NNUE and search pruning techniques.
   - **Cutechess ([`cutechess`](https://github.com/cutechess/cutechess))**: Tournament arbiter and CLI interface for engine matches.

1. **Large-Scale Data Engineering**:

   - **Live Zstandard Streaming**: Direct decompression and on-the-fly filtering of the multi-million puzzle/game database from `database.lichess.org` over HTTP without saving massive intermediate uncompressed files.
   - **Columnar Storage (Parquet / Arrow)**: Partitioned, compressed shards optimized for zero-copy queries.
   - **DuckDB Analytics**: Embedded analytical SQL queries for calculating engine agreement, solve accuracy, Average Centipawn Loss (ACPL), and depth distributions.

1. **Fault-Tolerant Resumable Execution**:

   - Automated checkpointing every 50 positions to allow interrupted benchmarks to resume immediately without duplicate computation.

1. **Tablebase Synergy**:

   - Integrated Syzygy 6-piece endgame tablebase probing (`.rtbw` / `.rtbz`).

______________________________________________________________________

## 2. Quick Start

### Installation & Environment

```bash
# Clone and enter directory
cd chess-ds

# Synchronize virtual environment with uv
uv sync

# Run automated tests
.venv/bin/pytest -v
```

### Stream Puzzles from Official Lichess Database

```bash
# Stream 5,000 Super-GM puzzles (Rating >= 2500) live into Parquet shards
.venv/bin/python -m chess_ds.cli fetch --min-rating 2500 --total 5000 --shard-size 1000
```

### Run Resumable Engine Benchmark

```bash
# Evaluate across engines with dynamic concurrency (automatically saved to database)
uv run python -m chess_ds.cli eval --total 5000 --movetime 500 --concurrency 2
```

### Display Rich Terminal Telemetry Summary

```bash
# Zero-copy DuckDB analytical rollup
uv run python -m chess_ds.cli summary
```

### Manual CSV Extraction via DuckDB Query

```bash
# Export custom SQL query result over Parquet database directly to CSV
uv run python -m chess_ds.cli export-csv \
  --query "SELECT engine, COUNT(*) as n, ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)*100, 2) as acc_pct, ROUND(AVG(nps), 0) as avg_nps, ROUND(AVG(depth), 1) as avg_depth FROM read_parquet('data/results/*.parquet') GROUP BY engine" \
  --output data/results/summary_export.csv
```

______________________________________________________________________

## 3. Storage Architecture: Database-First & Manual Export

- **Automatic Database Ingestion**: All engine evaluations, lookahead depths, and telemetry are stored automatically in compressed columnar **Apache Arrow / Parquet database tables** (`data/results/eval_*.parquet`) stamped with UTC ISO timestamps.
- **Manual CSV Generation**: Raw CSV files are never dumped automatically. CSV files are generated strictly on-demand as the output of targeted SQL queries via `chess_ds.cli export-csv`.
- **Live Observability**: Optional real-time experiment tracking with Weights & Biases via `--wandb`.

______________________________________________________________________

## 4. Code Quality & Tooling

- **Python Linter & Formatter**: `ruff`
- **Markdown Formatter**: `mdformat`
- **Type Checker**: `pyrefly`
- **Testing Framework**: `pytest`
