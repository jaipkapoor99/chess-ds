"""Test engine session initialization and FEN evaluation."""

from chess_ds.engines import EngineSession


def test_stockfish_session():
    engine = EngineSession("Stockfish 18")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    bm, depth, nps, _elapsed = engine.evaluate_fen(fen, movetime_ms=300)
    engine.close()
    assert len(bm) >= 4
    assert depth >= 5
    assert nps > 100000


def test_reckless_session():
    engine = EngineSession("Reckless 0.9.0")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    bm, depth, _nps, _elapsed = engine.evaluate_fen(fen, movetime_ms=300)
    engine.close()
    assert len(bm) >= 4
    assert depth >= 5


def test_lc0_session():
    engine = EngineSession("Lc0 v0.32.1")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    bm, _depth, _nps, _elapsed = engine.evaluate_fen(fen, movetime_ms=300)
    engine.close()
    assert len(bm) >= 4
