"""Test engine session initialization and FEN evaluation."""

import pytest

from chess_ds.engines import ENGINE_DEFAULTS, EngineSession


@pytest.mark.skipif(
    not ENGINE_DEFAULTS["Stockfish 18"]["binary"].exists(),
    reason="Stockfish binary not present in CI runner environment",
)
def test_stockfish_session():
    engine = EngineSession("Stockfish 18")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    bm, depth, nps, _elapsed = engine.evaluate_fen(fen, movetime_ms=300)
    engine.close()
    assert len(bm) >= 4
    assert depth >= 5
    assert nps > 100000


@pytest.mark.skipif(
    not ENGINE_DEFAULTS["Reckless 0.9.0"]["binary"].exists(),
    reason="Reckless binary not present in CI runner environment",
)
def test_reckless_session():
    engine = EngineSession("Reckless 0.9.0")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    bm, depth, _nps, _elapsed = engine.evaluate_fen(fen, movetime_ms=300)
    engine.close()
    assert len(bm) >= 4
    assert depth >= 5


@pytest.mark.skipif(
    not ENGINE_DEFAULTS["Lc0 v0.32.1"]["binary"].exists(),
    reason="Lc0 binary not present in CI runner environment",
)
def test_lc0_session():
    engine = EngineSession("Lc0 v0.32.1")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    bm, _depth, _nps, _elapsed = engine.evaluate_fen(fen, movetime_ms=300)
    engine.close()
    assert len(bm) >= 4
