# chess-ds: Chess Data Science & Engine Analytics Platform

A high-performance data science platform for chess analytics, puzzle benchmarking, opening novelty discovery, and neural vs. alpha-beta engine comparisons.

## Features

- **Engine Benchmarking Harness**: Orchestrates **Lc0 (Tensor Core GPU)**, **Stockfish 18 (AVX-512)**, and **Reckless 0.9.0** over custom FENs and massive puzzle datasets.
- **Data Pipelines**: High-speed querying of multi-million puzzle/game datasets using **DuckDB**, **Polars**, and **Pandas**.
- **Tablebase Synergy**: Integrated Syzygy 6-piece endgame tablebases.

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest
```
