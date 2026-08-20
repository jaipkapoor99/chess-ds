"""Engine management and UCI interface for Lc0, Stockfish, and Reckless."""

import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENGINES_DIR = ROOT_DIR / "engines"
WEIGHTS_DIR = ROOT_DIR / "weights"
SYZYGY_DIR = Path("/home/jaipkapoor99/Code/Syzygy-Tablebase-Downloader/combined_syzygy_tables")


ENGINE_DEFAULTS = {
    "Stockfish 18": {
        "binary": ENGINES_DIR / "stockfish-ubuntu-x86-64-avx512icl",
        "setup": [
            "uci",
            "setoption name Threads value 8",
            "setoption name Hash value 8192",
            f"setoption name SyzygyPath value {SYZYGY_DIR}",
            "isready",
        ],
    },
    "Reckless 0.9.0": {
        "binary": ENGINES_DIR / "reckless-linux-avx512",
        "setup": [
            "uci",
            "setoption name Threads value 8",
            "setoption name Hash value 8192",
            f"setoption name SyzygyPath value {SYZYGY_DIR}",
            "isready",
        ],
    },
    "Lc0 v0.32.1": {
        "binary": ENGINES_DIR / "lc0",
        "weights": WEIGHTS_DIR / "BT4-332.pb",
        "setup": [
            "uci",
            f"setoption name SyzygyPath value {SYZYGY_DIR}",
            "isready",
        ],
    },
}


class EngineSession:
    """Manages an active UCI session with an engine."""

    def __init__(self, name: str, threads: int = 8, _hash_mb: int = 8192):
        self.name = name
        cfg = ENGINE_DEFAULTS[name]
        cmd = [str(cfg["binary"])]
        if "weights" in cfg and cfg["weights"].exists():
            cmd.extend([f"--weights={cfg['weights']}", f"--threads={min(threads, 2)}"])

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for c in cfg["setup"]:
            self.process.stdin.write(c + "\n")
        self.process.stdin.flush()

    def evaluate_fen(self, fen: str, movetime_ms: int = 1000) -> tuple[str, int, float, float]:
        """Evaluates a FEN position. Returns (bestmove, depth, nps, elapsed_seconds)."""
        self.process.stdin.write(f"position fen {fen}\n")
        self.process.stdin.write(f"go movetime {movetime_ms}\n")
        self.process.stdin.flush()

        bestmove = ""
        depth = 0
        nps = 0.0
        start = time.time()

        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            l = line.strip()
            if "info" in l:
                parts = l.split()
                if "depth" in parts:
                    try:
                        depth = int(parts[parts.index("depth") + 1])
                    except ValueError, IndexError:
                        pass
                if "nps" in parts:
                    try:
                        nps = float(parts[parts.index("nps") + 1])
                    except ValueError, IndexError:
                        pass
            if "bestmove" in l:
                parts = l.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break

        return bestmove, depth, nps, time.time() - start

    def close(self):
        try:
            self.process.stdin.write("quit\n")
            self.process.stdin.flush()
            self.process.terminate()
        except OSError:
            pass
