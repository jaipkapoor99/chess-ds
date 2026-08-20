# ♟️ Engine Benchmark Results & Telemetry Analytics

This document records the empirical benchmarking results of leading open-source chess engines evaluated on the `chess-ds` platform across the partitioned Lichess tactical puzzle corpus.

______________________________________________________________________

## 1. Hardware & Test Environment

- **CPU**: AMD Ryzen 7 9800X3D 8-Core / 16-Thread Processor (Zen 5 microarchitecture, AVX-512)
- **GPU**: NVIDIA GeForce RTX 5090 (Blackwell Tensor Cores)
- **Neural Network Weights**: `BT4-332.pb` (Lc0 Policy-Value Transformer)
- **Endgame Tablebases**: Syzygy 6-piece `.rtbw` and `.rtbz` on NVMe SSD
- **Search Budget**: 500ms nominal per position
- **Evaluation Shards**: `lichess_shard_0000.parquet` through `lichess_shard_0099.parquet`
- **Mean Corpus Rating**: ~1,470 Tactical Elo

______________________________________________________________________

## 2. Consolidated Engine Analytics Summary

The following table summarizes the zero-copy DuckDB analytical rollup across all evaluated positions:

| Engine             | Total Puzzles | Solved | Accuracy (%) | Avg NPS (Nodes/sec) | Avg Depth | Avg Time / Pos (s) | Total Elapsed (s) |
| :----------------- | :------------ | :----- | :----------- | :------------------ | :-------- | :----------------- | :---------------- |
| **Reckless 0.9.0** | 5,005         | 4,989  | **99.68%**   | 18,817,059          | 51.6      | 0.336s             | 1,679.8s          |
| **Lc0 v0.32.1**    | 5,005         | 4,988  | **99.66%**   | 56,616              | 7.2       | **0.164s**         | **818.7s**        |
| **Stockfish 18**   | 5,025         | 5,006  | **99.62%**   | **21,915,469**      | **90.5**  | 0.345s             | 1,735.8s          |

______________________________________________________________________

## 3. Key Pedagogical Insights & Paradigm Comparison

### 1. Neural MCTS vs. Alpha-Beta Search Efficiency

- **Leela Chess Zero (Lc0 v0.32.1)** achieved **99.66% accuracy** at an average depth of just **7.2 plies** and **56,616 nodes per second**, thanks to the policy-value Transformer evaluation running on Tensor Cores.
- In contrast, **Stockfish 18** and **Reckless 0.9.0** evaluated at **18M–22M nodes per second**, requiring depths of **51.6–90.5 plies** to achieve equivalent accuracy.
- **Result**: Neural evaluation spends vastly more compute per node, but prunes trillions of fruitless subtrees through policy priors.

### 2. Time-to-Solution Throughput

- **Lc0 completed the 5,005-position dataset in 818.7 seconds** (averaging 0.164s per position), solving high-confidence tactical moves nearly twice as fast as CPU engines due to fast neural bestmove convergence.
- **Stockfish 18 and Reckless 0.9.0** sustained high search depths (~90 plies on tactical lines) on the AMD Ryzen 7 9800X3D with AVX-512 SIMD vectorization.

______________________________________________________________________

## 4. Querying Raw Telemetry

To reproduce or slice these results directly from the Parquet database tables:

```sql
SELECT
    engine,
    COUNT(*) as total_puzzles,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as solved,
    ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) * 100.0, 2) as accuracy_pct,
    ROUND(AVG(nps), 0) as avg_nps,
    ROUND(AVG(depth), 1) as avg_depth,
    ROUND(AVG(elapsed_seconds), 3) as avg_sec_per_pos,
    ROUND(AVG(rating), 0) as avg_puzzle_rating
FROM read_parquet('data/results/eval_*.parquet')
GROUP BY engine
ORDER BY accuracy_pct DESC, avg_nps DESC;
```
