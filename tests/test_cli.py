"""Tests for CLI parser commands: eval, fetch, summary, and export-csv."""

from unittest.mock import patch

import pytest

from chess_ds.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        with patch("sys.argv", ["chess_ds", "--help"]):
            main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "eval" in captured.out
    assert "fetch" in captured.out
    assert "summary" in captured.out
    assert "export-csv" in captured.out


def test_cli_export_csv_parser():
    with patch("sys.argv", ["chess_ds", "export-csv", "--output", "data/results/test.csv"]):
        with patch(
            "chess_ds.evaluator.ResumableBenchmarkRunner.export_csv_from_query"
        ) as mock_export:
            main()
            mock_export.assert_called_once()


def test_cli_export_pgn_parser():
    with patch(
        "sys.argv",
        ["chess_ds", "export-pgn", "--input", "data/results/matches/test.pgn"],
    ):
        with patch("chess_ds.match_ingest.enrich_and_export_pgn") as mock_export_pgn:
            main()
            mock_export_pgn.assert_called_once()
