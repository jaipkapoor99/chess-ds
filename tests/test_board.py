from chess_ds.board import render_board_svg, uci_to_san


def test_uci_to_san():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    san = uci_to_san(fen, "e2e4")
    assert san == "e4"

    fen_tactics = "r1bqk2r/pppp1ppp/2n5/1B2p3/4n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    san_tactics = uci_to_san(fen_tactics, "d1e2")
    assert san_tactics == "Qe2"


def test_render_board_svg():
    fen = "r1bqk2r/pppp1ppp/2n5/1B2p3/4n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5"
    svg = render_board_svg(fen, solution_uci="d1e2", engine_move_uci="d2d4")
    assert "<svg" in svg
    assert "</svg>" in svg
