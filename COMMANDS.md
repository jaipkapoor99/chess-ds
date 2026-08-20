# Terminal Commands & CLI Reference

This document provides clean, repository-relative terminal commands for operating the `chess-ds` platform.

> [!NOTE]
> **Benchmarking Script Flexibility**: Exact evaluation and benchmarking scripts vary widely depending on user hardware topologies (CUDA GPU Tensor Core allocations vs. AVX-512 CPU thread counts), search budgets, and concurrency schedules. The commands below provide flexible CLI primitives and modular patterns that can be tailored to any benchmarking experiment.

______________________________________________________________________

## 1. Environment & Setup

### Synchronize virtual environment with uv

```bash
uv sync
```

### Activate virtual environment

```bash
source .venv/bin/activate
```

### Run test suite and static type checking

```bash
uv run pytest -v
uv run pyrefly check
uv run ruff check .
uv run ruff format --check .
uv run mdformat --check README.md COMMANDS.md
```

______________________________________________________________________

## 2. Lichess Data Streaming & Sharding

### Stream ultra-hard puzzles (Rating >= 2500, 5,000 puzzles, shards of 1,000)

```bash
uv run python -m chess_ds.cli fetch --min-rating 2500 --total 5000 --shard-size 1000
```

### Stream Super-GM puzzles (Rating >= 2700, 2,000 puzzles)

```bash
uv run python -m chess_ds.cli fetch --min-rating 2700 --total 2000 --shard-size 500
```

### Stream entire database (Full historical dataset, shards of 50,000)

```bash
uv run python -m chess_ds.cli fetch --min-rating 0 --total 5000000 --shard-size 50000
```

______________________________________________________________________

## 3. Engine Benchmark & Evaluation

> [!NOTE]
> **Automatic Database Ingestion**: All benchmarks automatically persist evaluation telemetry directly to the Parquet/DuckDB database in `data/results/` with ISO timestamps and resume checkpoints.

### 1. Start a New Benchmark Run (Automatically creates Run ID and saves manifest)

```bash
uv run python -m chess_ds.cli eval --total 5000 --movetime 500 --concurrency 2
```

### 2. Resume an Interrupted Run (Auto-recovers all parameters & metadata from Run ID)

```bash
uv run python -m chess_ds.cli eval --resume run_20260820_125300
```

### 3. Evaluate with Live Weights & Biases Telemetry Streaming

```bash
uv run python -m chess_ds.cli eval --total 5000 --movetime 500 --concurrency 2 --wandb --wandb-project chess-ds
```

### 4. Deep Lookahead Benchmark (2.0s search budget)

```bash
uv run python -m chess_ds.cli eval --total 500 --movetime 2000 --concurrency 1
```

______________________________________________________________________

## 4. Analytics & Manual CSV Extraction

### View Rich terminal telemetry summary (Zero-copy DuckDB rollup)

```bash
uv run python -m chess_ds.cli summary
```

### Manual CSV Extraction via DuckDB Query

```bash
uv run python -m chess_ds.cli export-csv \
  --query "SELECT engine, COUNT(*) as n, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as solved, ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)*100, 2) as acc_pct, ROUND(AVG(nps), 0) as avg_nps, ROUND(AVG(depth), 1) as avg_depth, ROUND(AVG(elapsed_seconds), 3) as avg_sec FROM read_parquet('data/results/*.parquet') GROUP BY engine ORDER BY acc_pct DESC" \
  --output data/results/benchmark_summary.csv
```

### Export solved tactical positions to CSV

```bash
uv run python -m chess_ds.cli export-csv \
  --query "SELECT puzzle_id, rating, engine, depth, nps, elapsed_seconds FROM read_parquet('data/results/*.parquet') WHERE is_correct = true" \
  --output data/results/solved_tactics.csv
```

______________________________________________________________________

## 5. Direct Engine Match Commands (Cutechess-CLI)

### Run 10-game match: Lc0 vs Stockfish 18

```bash
./engines/cutechess-cli \
  -engine name=Lc0 cmd=./engines/lc0 dir=./engines option.WeightsFile=./weights/BT4-332.pb option.Threads=2 option.SyzygyPath=./syzygy \
  -engine name=Stockfish18 cmd=./engines/stockfish-ubuntu-x86-64-avx512icl dir=./engines option.Threads=8 option.Hash=8192 option.SyzygyPath=./syzygy \
  -each proto=uci tc=10+0.2 \
  -rounds 10 \
  -repeat \
  -concurrency 1 \
  -draw movenumber=40 movecount=8 score=10 \
  -resign movecount=4 score=700 \
  -pgnout ./data/results/match_lc0_vs_sf.pgn
```

### Run 10-game match: Lc0 vs Reckless 0.9.0

```bash
./engines/cutechess-cli \
-engine name=Lc0 cmd=./engines/lc0 dir=./engines option.WeightsFile=./weights/BT4-332.pb option.Threads=2 option.SyzygyPath=./syzygy \
-engine name=Stockfish18 cmd=./engines/stockfish-ubuntu-x86-64-avx512icl dir=./engines option.Threads=8 option.Hash=8192 option.SyzygyPath=./syzygy \
-each proto=uci tc=10+0.2 \
-rounds 10 \
-repeat \
-concurrency 1 \
-draw movenumber=40 movecount=8 score=10 \
-resign movecount=4 score=700 \
-pgnout ./data/results/match_lc0_vs_sf.pgn

```
