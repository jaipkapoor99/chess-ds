"""Tests for 3NF Relational Database DDL, Constraints, and Zero-Copy DuckDB Queries."""

from pathlib import Path

import duckdb

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src" / "chess_ds" / "schema.sql"


def test_schema_compilation():
    """Verifies that schema.sql compiles with 0 syntax errors in DuckDB."""
    con = duckdb.connect(":memory:")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        ddl = f.read()
    con.execute(ddl)

    # Verify tables exist
    tables = con.execute("SHOW TABLES").fetchall()
    table_names = {t[0] for t in tables}
    expected = {
        "players",
        "openings",
        "engines",
        "themes",
        "benchmark_runs",
        "puzzles",
        "puzzle_themes",
        "puzzle_evaluations",
        "games",
        "game_moves",
    }
    assert expected.issubset(table_names)


def test_3nf_relational_integrity():
    """Verifies foreign key relationships and analytical SQL rollups across 3NF tables."""
    con = duckdb.connect(":memory:")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        ddl = f.read()
    con.execute(ddl)

    # Insert dimensions
    con.execute(
        "INSERT INTO engines VALUES ('stockfish_18', 'Stockfish 18', '18.0', 'Alpha_Beta_NNUE', 'CPU_AVX512');"
    )
    con.execute(
        "INSERT INTO engines VALUES ('lc0_v0_32_1', 'Lc0 v0.32.1', '0.32.1', 'Neural_MCTS', 'GPU_TensorCore');"
    )
    con.execute(
        "INSERT INTO benchmark_runs VALUES ('run_test_01', 500, 2, 'wandb_test', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);"
    )
    con.execute(
        "INSERT INTO puzzles VALUES ('puz_01', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 'e2e4', 2600, 50, 95, 200, 'https://lichess.org/test1', '2026-08-20');"
    )
    con.execute(
        "INSERT INTO puzzles VALUES ('puz_02', 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1', 'e7e5', 2700, 45, 99, 400, 'https://lichess.org/test2', '2026-08-20');"
    )
    con.execute("INSERT INTO themes VALUES ('crushing', 'Crushing advantage');")
    con.execute("INSERT INTO themes VALUES ('opening', 'Opening tactics');")
    con.execute("INSERT INTO puzzle_themes VALUES ('puz_01', 'opening');")
    con.execute("INSERT INTO puzzle_themes VALUES ('puz_02', 'crushing');")

    # Insert evaluations
    con.execute(
        "INSERT INTO puzzle_evaluations VALUES ('run_test_01', 'puz_01', 'stockfish_18', 'e2e4', true, 28, 20000000.0, 0.45, CURRENT_TIMESTAMP);"
    )
    con.execute(
        "INSERT INTO puzzle_evaluations VALUES ('run_test_01', 'puz_02', 'stockfish_18', 'e7e5', true, 30, 22000000.0, 0.48, CURRENT_TIMESTAMP);"
    )
    con.execute(
        "INSERT INTO puzzle_evaluations VALUES ('run_test_01', 'puz_01', 'lc0_v0_32_1', 'e2e4', true, 20, 85000.0, 0.49, CURRENT_TIMESTAMP);"
    )
    con.execute(
        "INSERT INTO puzzle_evaluations VALUES ('run_test_01', 'puz_02', 'lc0_v0_32_1', 'c7c5', false, 19, 84000.0, 0.49, CURRENT_TIMESTAMP);"
    )

    # Analytical Join Query
    query = """
    SELECT
        e.engine_name,
        COUNT(*) as total,
        SUM(CASE WHEN pe.is_correct THEN 1 ELSE 0 END) as solved,
        ROUND(AVG(CASE WHEN pe.is_correct THEN 1.0 ELSE 0.0 END) * 100.0, 2) as accuracy_pct
    FROM puzzle_evaluations pe
    JOIN engines e ON pe.engine_id = e.engine_id
    WHERE pe.run_id = 'run_test_01'
    GROUP BY e.engine_name
    ORDER BY accuracy_pct DESC
    """
    df = con.execute(query).pl()
    assert len(df) == 2
    row_sf = df.filter(df["engine_name"] == "Stockfish 18").to_dicts()[0]
    row_lc0 = df.filter(df["engine_name"] == "Lc0 v0.32.1").to_dicts()[0]
    assert row_sf["accuracy_pct"] == 100.0
    assert row_lc0["accuracy_pct"] == 50.0
