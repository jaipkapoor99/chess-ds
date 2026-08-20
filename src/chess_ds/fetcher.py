"""Official Lichess Pipeline:
- Fetch live puzzles via Berserk client
- Stream & filter the official full Lichess Puzzle Database (database.lichess.org) over HTTP with Zstandard
"""

import io
import urllib.request
from collections.abc import Generator
from pathlib import Path

import berserk
import chess
import pyarrow as pa
import pyarrow.parquet as pq
import zstandard
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
SHARDS_DIR = DATA_DIR / "shards"
LICHESS_PUZZLE_DB_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"


class LichessFetcher:
    """Fetches puzzles from Lichess via Berserk API and ZStandard database streaming."""

    def __init__(self, api_token: str | None = None):
        session = berserk.TokenSession(api_token) if api_token else None
        self.client = berserk.Client(session=session)

    def get_daily_puzzle(self) -> dict:
        """Fetches the official Daily Puzzle from Lichess via Berserk."""
        return self.client.puzzles.get_daily()

    def get_puzzle_by_id(self, puzzle_id: str) -> dict:
        """Fetches a specific puzzle metadata by ID from Lichess via Berserk."""
        return self.client.puzzles.get(puzzle_id)

    @staticmethod
    def stream_official_database(
        min_rating: int = 2500,
        popularity_min: int = 80,
    ) -> Generator[dict]:
        """Streams the official multi-million Lichess puzzle database live over HTTP.
        Decompresses on the fly with zero temporary file footprint on disk.
        """
        req = urllib.request.Request(
            LICHESS_PUZZLE_DB_URL,
            headers={"User-Agent": "chess-ds-pipeline/0.1.0"},
        )

        with urllib.request.urlopen(req) as resp:
            dctx = zstandard.ZstdDecompressor()
            stream_reader = dctx.stream_reader(resp)
            text_stream = io.TextIOWrapper(stream_reader, encoding="utf-8")

            # Read header
            header_line = text_stream.readline().strip()
            headers = [h.strip() for h in header_line.split(",")]

            p_id_idx = headers.index("PuzzleId")
            fen_idx = headers.index("FEN")
            moves_idx = headers.index("Moves")
            rating_idx = headers.index("Rating")
            pop_idx = headers.index("Popularity") if "Popularity" in headers else -1
            themes_idx = headers.index("Themes") if "Themes" in headers else -1

            for line in text_stream:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < len(headers):
                    continue

                try:
                    rating = int(parts[rating_idx])
                    pop = int(parts[pop_idx]) if pop_idx != -1 else 100
                except ValueError, IndexError:
                    continue

                if rating < min_rating or pop < popularity_min:
                    continue

                moves_list = parts[moves_idx].split()
                if len(moves_list) < 2:
                    continue

                try:
                    board = chess.Board(parts[fen_idx])
                    blunder = chess.Move.from_uci(moves_list[0])
                    board.push(blunder)
                    puzzle_fen = board.fen()
                    solution = moves_list[1]
                except ValueError, IndexError, chess.IllegalMoveError:
                    continue

                yield {
                    "puzzle_id": parts[p_id_idx],
                    "fen": puzzle_fen,
                    "solution": solution,
                    "rating": rating,
                    "popularity": pop,
                    "themes": parts[themes_idx] if themes_idx != -1 else "",
                }

    @classmethod
    def build_live_parquet_shards(
        cls,
        min_rating: int = 2500,
        popularity_min: int = 80,
        total_puzzles: int = 10000,
        shard_size: int = 1000,
    ) -> list[Path]:
        """Streams live from Lichess and saves partitioned Parquet shards."""
        SHARDS_DIR.mkdir(parents=True, exist_ok=True)
        print(
            f"\n📡 Streaming {total_puzzles:,} ultra-hard puzzles (Rating >= {min_rating}) live from official Lichess repository..."
        )

        schema = pa.schema(
            [
                ("puzzle_id", pa.string()),
                ("fen", pa.string()),
                ("solution", pa.string()),
                ("rating", pa.int32()),
                ("popularity", pa.int32()),
                ("themes", pa.string()),
            ]
        )

        shards_created: list[Path] = []
        current_rows: list[dict] = []
        shard_idx = 0

        pbar = tqdm(total=total_puzzles, desc="Streaming Lichess Database", unit="pos")

        for puzzle in cls.stream_official_database(
            min_rating=min_rating, popularity_min=popularity_min
        ):
            current_rows.append(puzzle)
            pbar.update(1)

            if len(current_rows) >= shard_size:
                shard_path = SHARDS_DIR / f"lichess_shard_{shard_idx:04d}.parquet"
                table = pa.Table.from_pylist(current_rows, schema=schema)
                pq.write_table(table, shard_path, compression="zstd")
                shards_created.append(shard_path)
                shard_idx += 1
                current_rows = []

            if len(shards_created) * shard_size + len(current_rows) >= total_puzzles:
                break

        if current_rows:
            shard_path = SHARDS_DIR / f"lichess_shard_{shard_idx:04d}.parquet"
            table = pa.Table.from_pylist(current_rows, schema=schema)
            pq.write_table(table, shard_path, compression="zstd")
            shards_created.append(shard_path)

        pbar.close()
        print(
            f"✓ Successfully created {len(shards_created)} fresh Parquet shards directly from official Lichess database.\n"
        )
        return shards_created
