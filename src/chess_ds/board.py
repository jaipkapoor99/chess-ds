"""Chess board utilities: move validation, algebraic SAN conversion, and SVG diagram rendering."""

from pathlib import Path

import chess
import chess.svg


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


def render_board_svg(
    fen: str,
    solution_uci: str | None = None,
    engine_move_uci: str | None = None,
    size: int = 400,
    output_path: Path | None = None,
) -> str:
    """Renders a high-resolution SVG diagram of the board position with color-coded move arrows:
    - Green Arrow: Ground-truth tactical solution.
    - Red Arrow: Engine candidate move (if divergent from solution).
    """
    try:
        board = chess.Board(fen)
        arrows: list[chess.svg.Arrow] = []

        if solution_uci:
            try:
                m_sol = chess.Move.from_uci(solution_uci)
                arrows.append(
                    chess.svg.Arrow(m_sol.from_square, m_sol.to_square, color="#00cc66cc")
                )
            except ValueError:
                pass

        if engine_move_uci and engine_move_uci != solution_uci:
            try:
                m_eng = chess.Move.from_uci(engine_move_uci)
                arrows.append(
                    chess.svg.Arrow(m_eng.from_square, m_eng.to_square, color="#ff3333cc")
                )
            except ValueError:
                pass

        svg_content = chess.svg.board(
            board=board,
            arrows=arrows,
            size=size,
            orientation=board.turn,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

        return svg_content
    except Exception as e:
        return f"<!-- Error rendering SVG: {e} -->"
