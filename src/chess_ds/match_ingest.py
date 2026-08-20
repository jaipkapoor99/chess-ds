"""Match Ingestion: Automatically parses cutechess PGN match outputs into 3NF Parquet Database Tables."""

from datetime import datetime, timezone
from pathlib import Path

import chess.pgn
import polars as pl

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "results" / "matches"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def ingest_match_pgn(
    pgn_path: Path,
    match_id: str,
    engine1: str,
    engine2: str,
    time_control: str,
    total_rounds: int,
) -> tuple[Path, Path]:
    """Parses match PGN file and writes 3NF relational tables:
    - engine_matches: data/results/matches/engine_matches_{match_id}.parquet
    - engine_match_games: data/results/matches/engine_match_games_{match_id}.parquet
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")

    games_records = []
    e1_score = 0.0
    e2_score = 0.0
    draws = 0
    game_idx = 1
    started_at = None
    completed_at = None

    e1_lower = engine1.lower()
    e2_lower = engine2.lower()

    with open(pgn_path, encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            headers = game.headers
            white = headers.get("White", "")
            black = headers.get("Black", "")
            result = headers.get("Result", "*")
            plies = int(headers.get("PlyCount", len(list(game.mainline()))))
            termination = headers.get("Termination", "Normal")
            start_time_str = headers.get("GameStartTime")
            end_time_str = headers.get("GameEndTime")

            if started_at is None and start_time_str:
                started_at = start_time_str
            if end_time_str:
                completed_at = end_time_str

            # Map engine IDs
            white_id = (
                e1_lower
                if e1_lower in white.lower()
                else (e2_lower if e2_lower in white.lower() else white.lower())
            )
            black_id = (
                e2_lower
                if e2_lower in black.lower()
                else (e1_lower if e1_lower in black.lower() else black.lower())
            )

            # Score accounting
            if result == "1-0":
                if white_id == e1_lower:
                    e1_score += 1.0
                else:
                    e2_score += 1.0
            elif result == "0-1":
                if black_id == e1_lower:
                    e1_score += 1.0
                else:
                    e2_score += 1.0
            elif result == "1/2-1/2":
                e1_score += 0.5
                e2_score += 0.5
                draws += 1

            games_records.append(
                {
                    "game_id": f"{match_id}_g{game_idx}",
                    "match_id": match_id,
                    "round_number": int(headers.get("Round", game_idx)),
                    "white_engine_id": white_id,
                    "black_engine_id": black_id,
                    "result": result,
                    "total_plies": plies,
                    "termination": termination,
                    "played_at": end_time_str or datetime.now(timezone.utc).isoformat(),
                }
            )
            game_idx += 1

    # Match summary record
    now_iso = datetime.now(timezone.utc).isoformat()
    match_record = [
        {
            "match_id": match_id,
            "engine1_id": e1_lower,
            "engine2_id": e2_lower,
            "time_control": time_control,
            "total_rounds": total_rounds,
            "concurrency": 1,
            "engine1_score": float(e1_score),
            "engine2_score": float(e2_score),
            "draws": int(draws),
            "pgn_path": str(pgn_path),
            "started_at": started_at or now_iso,
            "completed_at": completed_at or now_iso,
        }
    ]

    df_matches = pl.DataFrame(match_record)
    df_games = pl.DataFrame(games_records)

    matches_parquet = RESULTS_DIR / f"engine_matches_{match_id}.parquet"
    games_parquet = RESULTS_DIR / f"engine_match_games_{match_id}.parquet"

    df_matches.write_parquet(matches_parquet)
    df_games.write_parquet(games_parquet)

    return matches_parquet, games_parquet


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 7:
        pgn = Path(sys.argv[1])
        m_id = sys.argv[2]
        eng1 = sys.argv[3]
        eng2 = sys.argv[4]
        tc = sys.argv[5]
        rounds = int(sys.argv[6])
        m_p, g_p = ingest_match_pgn(pgn, m_id, eng1, eng2, tc, rounds)
        print(f"✓ Ingested Match into Parquet DB: {m_p}")
        print(f"✓ Ingested Match Games into Parquet DB: {g_p}")
