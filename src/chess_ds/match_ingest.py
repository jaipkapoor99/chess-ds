import re
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn
import polars as pl

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "results" / "matches"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def parse_move_telemetry(comment: str) -> tuple[float | None, int | None, float | None]:
    """Parses move comments like '{+0.86/16 0.49s}' or '{-0.78/10 0.65s, Draw by ...}'.
    Returns (eval_score, depth, elapsed_seconds).
    """
    eval_score = None
    depth = None
    elapsed = None

    if not comment:
        return eval_score, depth, elapsed

    # Match eval and depth e.g. +0.86/16 or -1.05/20 or #+3/25
    m_eval_depth = re.search(r"([+-]?\d+\.?\d*|\#?[+-]?\d+)/(\d+)", comment)
    if m_eval_depth:
        try:
            eval_score = float(m_eval_depth.group(1).replace("#", ""))
            depth = int(m_eval_depth.group(2))
        except ValueError:
            pass

    # Match elapsed time e.g. 0.49s or 1.8s
    m_time = re.search(r"(\d+\.?\d*)s", comment)
    if m_time:
        try:
            elapsed = float(m_time.group(1))
        except ValueError:
            pass

    return eval_score, depth, elapsed


def enrich_and_export_pgn(input_pgn_path: Path, output_pgn_path: Path | None = None) -> Path:
    """Parses raw match PGN, computes average depth, time per move, and speed metrics for both White
    and Black engines, writes telemetry headers to every game, and outputs an annotated PGN file.
    """
    if not input_pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {input_pgn_path}")

    target_path = output_pgn_path or input_pgn_path.with_name(
        f"{input_pgn_path.stem}_annotated.pgn"
    )

    enriched_games = []
    with open(input_pgn_path, encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            w_depths, b_depths = [], []
            w_times, b_times = [], []

            # Traverse moves and extract telemetry comments
            is_white_turn = True

            # If custom FEN, check initial turn
            if "FEN" in game.headers:
                try:
                    init_board = chess.Board(game.headers["FEN"])
                    is_white_turn = init_board.turn == chess.WHITE
                except Exception:
                    pass

            for node in game.mainline():
                comment = node.comment
                _ev, d, t = parse_move_telemetry(comment)
                if is_white_turn:
                    if d is not None:
                        w_depths.append(d)
                    if t is not None:
                        w_times.append(t)
                else:
                    if d is not None:
                        b_depths.append(d)
                    if t is not None:
                        b_times.append(t)
                is_white_turn = not is_white_turn

            # Calculate averages
            w_avg_d = sum(w_depths) / len(w_depths) if w_depths else 0.0
            b_avg_d = sum(b_depths) / len(b_depths) if b_depths else 0.0
            w_avg_t = sum(w_times) / len(w_times) if w_times else 0.0
            b_avg_t = sum(b_times) / len(b_times) if b_times else 0.0

            # Attach enriched telemetry headers
            game.headers["WhiteAvgDepth"] = f"{w_avg_d:.1f}"
            game.headers["BlackAvgDepth"] = f"{b_avg_d:.1f}"
            game.headers["WhiteAvgMoveTime"] = f"{w_avg_t:.3f}s"
            game.headers["BlackAvgMoveTime"] = f"{b_avg_t:.3f}s"
            game.headers["Annotator"] = "chess-ds telemetry engine"

            enriched_games.append(game)

    # Write enriched PGN
    with open(target_path, "w", encoding="utf-8") as f_out:
        for g in enriched_games:
            exporter = chess.pgn.FileExporter(f_out, headers=True, comments=True, variations=True)
            g.accept(exporter)
            f_out.write("\n\n")

    return target_path


def ingest_match_pgn(
    pgn_path: Path,
    match_id: str,
    engine1: str,
    engine2: str,
    time_control: str,
    total_rounds: int,
) -> tuple[Path, Path, Path]:
    """Parses match PGN file, enriches telemetry tags, and writes 3NF relational tables:
    - engine_matches: data/results/matches/engine_matches_{match_id}.parquet
    - engine_match_games: data/results/matches/engine_match_games_{match_id}.parquet
    - enriched_pgn: data/results/matches/{match_id}_annotated.pgn
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")

    # 1. Generate enriched PGN with telemetry tags
    enriched_pgn_path = enrich_and_export_pgn(pgn_path)

    games_records = []
    e1_score = 0.0
    e2_score = 0.0
    draws = 0
    game_idx = 1
    started_at = None
    completed_at = None

    e1_lower = engine1.lower()
    e2_lower = engine2.lower()

    with open(enriched_pgn_path, encoding="utf-8") as f:
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
            "pgn_path": str(enriched_pgn_path),
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

    return matches_parquet, games_parquet, enriched_pgn_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 7:
        pgn = Path(sys.argv[1])
        m_id = sys.argv[2]
        eng1 = sys.argv[3]
        eng2 = sys.argv[4]
        tc = sys.argv[5]
        rounds = int(sys.argv[6])
        m_p, g_p, e_p = ingest_match_pgn(pgn, m_id, eng1, eng2, tc, rounds)
        print(f"✓ Ingested Match into Parquet DB: {m_p}")
        print(f"✓ Ingested Match Games into Parquet DB: {g_p}")
        print(f"✓ Enriched PGN with Telemetry Headers: {e_p}")
