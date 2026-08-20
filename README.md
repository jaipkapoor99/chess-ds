# `chess-ds`: Pedagogical Chess Data Science & Engine Analytics Platform

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
# Evaluate all shards across Lc0, Reckless, and Stockfish (500ms per position)
.venv/bin/python -m chess_ds.cli eval --movetime 500
```

### Display DuckDB Consolidated Analytics

```bash
.venv/bin/python -m chess_ds.cli summary
```

______________________________________________________________________

## 3. Code Quality & Tooling

- **Python Linter & Formatter**: `ruff`
- **Markdown Formatter**: `mdformat`
- **Type Checker**: `pyrefly`
- **Testing Framework**: `pytest`
