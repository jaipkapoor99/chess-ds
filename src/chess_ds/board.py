"""Chess board utilities: move validation and algebraic SAN conversion."""

import chess


def uci_to_san(fen: str, uci_move: str) -> str:
    """Converts a UCI move string (e.g. 'e2e4') into Standard Algebraic Notation (e.g. 'e4', 'Nf3', 'Qxf7#')."""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci_move)
        if move in board.legal_moves:
            return board.san(move)
        return uci_move
    except Exception:
        return uci_move
