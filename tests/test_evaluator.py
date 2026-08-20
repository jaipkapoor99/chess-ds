"""Tests for ResumableBenchmarkRunner, database persistence, and manual SQL CSV export."""

from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from chess_ds.evaluator import ResumableBenchmarkRunner


def test_evaluator_database_persistence_and_manual_csv(tmp_path: Path):
    """Verifies that evaluations persist automatically to Parquet and CSV is produced ONLY via manual export."""
    # Create sample puzzle shard
    puzzles = [
        {
            "puzzle_id": "test_01",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "solution": "e2e4",
            "rating": 2500,
            "rating_deviation": 50,
            "popularity": 95,
            "nb_plays": 100,
            "themes": "opening",
            "game_url": "https://lichess.org/test1",
        },
        {
            "puzzle_id": "test_02",
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            "solution": "e7e5",
            "rating": 2600,
            "rating_deviation": 45,
            "popularity": 98,
            "nb_plays": 200,
            "themes": "crushing",
            "game_url": "https://lichess.org/test2",
        },
    ]
    shard_file = tmp_path / "shard_test.parquet"
    table = pa.Table.from_pylist(puzzles)
    pq.write_table(table, shard_file)

    # Initialize runner with test run ID
    runner = ResumableBenchmarkRunner(
        movetime_ms=100,
        run_id="test_run_auto_db",
        use_wandb=False,
        total_puzzles=2,
        concurrency=1,
        engines=["Stockfish 18"],
    )

    # Evaluate shard
    res = runner.evaluate_shard_with_engine("Stockfish 18", shard_file)
    assert res["status"] == "completed"
    assert res["total"] == 2

    # Verify Parquet database table exists automatically
    parquet_path = Path(res["result_path"])
    assert parquet_path.exists()
    df_eval = pl.read_parquet(parquet_path)
    assert len(df_eval) == 2
    assert "solution_san" in df_eval.columns
    assert "engine_move_san" in df_eval.columns
    assert "evaluated_at" in df_eval.columns

    # Verify NO automatic CSV was produced in the directory
    csv_files = list(parquet_path.parent.glob("*.csv"))
    # (Any CSV in data/results should not match this run automatically)
    assert not any("test_run_auto_db" in f.name for f in csv_files)

    # Test MANUAL CSV Extraction via DuckDB Query
    manual_csv_path = tmp_path / "manual_extracted_summary.csv"
    query = f"""
    SELECT
        engine,
        COUNT(*) as total,
        ROUND(AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)*100, 2) as accuracy_pct
    FROM read_parquet('{parquet_path}')
    GROUP BY engine
    """
    ResumableBenchmarkRunner.export_csv_from_query(query, manual_csv_path)

    # Verify manual CSV was successfully produced with headers
    assert manual_csv_path.exists()
    content = manual_csv_path.read_text()
    assert "engine,total,accuracy_pct" in content
    assert "Stockfish 18" in content
