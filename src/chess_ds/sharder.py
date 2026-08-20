"""Streams ultra-hard puzzles (Rating >= 2500) and shards them into Parquet files."""

import csv
from pathlib import Path

import chess
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CSV_PATH = Path("/home/jaipkapoor99/Desktop/lichess_puzzle_transformed.csv")
SHARDS_DIR = ROOT_DIR / "data" / "shards"


def build_puzzle_shards(
    min_rating: int = 2500,
    total_target: int = 10000,
    shard_size: int = 1000,
) -> list[Path]:
    """Filters dataset for rating >= min_rating, parses FENs, and saves Parquet shards."""
    SHARDS_DIR.mkdir(parents=True, exist_ok=True)

    # Check existing shards
    existing_shards = sorted(SHARDS_DIR.glob("shard_*.parquet"))
    if existing_shards:
        print(f"✓ Found {len(existing_shards)} existing parquet shards in {SHARDS_DIR}")
        return existing_shards

    print(
        f"Extracting {total_target:,} ultra-hard puzzles (Rating >= {min_rating}) into shards of {shard_size}..."
    )

    schema = pa.schema(
        [
            ("puzzle_id", pa.string()),
            ("fen", pa.string()),
            ("solution", pa.string()),
            ("rating", pa.int32()),
            ("themes", pa.string()),
            ("game_url", pa.string()),
        ]
    )

    current_shard_rows: list[dict] = []
    shard_index = 0
    shards_created: list[Path] = []

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        pbar = tqdm(total=total_target, desc="Sharding Ultra-Hard Puzzles")

        for row in reader:
            try:
                rating = int(row.get("Rating", 0))
            except (ValueError, TypeError):
                continue

            if rating < min_rating:
                continue

            moves_list = row.get("Moves", "").split()
            if len(moves_list) < 2:
                continue

            try:
                board = chess.Board(row["FEN"])
                blunder_move = chess.Move.from_uci(moves_list[0])
                board.push(blunder_move)
                puzzle_fen = board.fen()
                solution = moves_list[1]
            except (ValueError, IndexError, chess.IllegalMoveError):
                continue

            current_shard_rows.append(
                {
                    "puzzle_id": row.get("PuzzleId", f"{shard_index}_{len(current_shard_rows)}"),
                    "fen": puzzle_fen,
                    "solution": solution,
                    "rating": rating,
                    "themes": row.get("Themes", ""),
                    "game_url": row.get("GameUrl", ""),
                }
            )
            pbar.update(1)

            if len(current_shard_rows) >= shard_size:
                shard_path = SHARDS_DIR / f"shard_{shard_index:04d}.parquet"
                table = pa.Table.from_pylist(current_shard_rows, schema=schema)
                pq.write_table(table, shard_path, compression="zstd")
                shards_created.append(shard_path)
                shard_index += 1
                current_shard_rows = []

            if (shard_index * shard_size + len(current_shard_rows)) >= total_target:
                break

        if current_shard_rows:
            shard_path = SHARDS_DIR / f"shard_{shard_index:04d}.parquet"
            table = pa.Table.from_pylist(current_shard_rows, schema=schema)
            pq.write_table(table, shard_path, compression="zstd")
            shards_created.append(shard_path)

        pbar.close()

    print(f"✓ Created {len(shards_created)} Parquet shards ({total_target:,} puzzles total).")
    return shards_created


if __name__ == "__main__":
    build_puzzle_shards(min_rating=2500, total_target=10000, shard_size=1000)
