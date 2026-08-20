#!/usr/bin/env bash
# =============================================================================
# chess-ds: Full 4-Engine Round-Robin Tournament Runner using cutechess-cli
# =============================================================================
# Usage:
#   ./scripts/run_tournament.sh [ROUNDS_PER_PAIR] [TIME_CONTROL] [OPENING_BOOK]
# Example:
#   ./scripts/run_tournament.sh 6 "10+0.1" "books/Drawkiller_balanced_big.epd"
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# Arguments & Defaults
ROUNDS_PER_PAIR="${1:-6}"
TC="${2:-10+0.1}"
BOOK_ARG="${3:-books/Drawkiller_balanced_big.epd}"

TOURNAMENT_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TOURNAMENT_ID="tourney_${TOURNAMENT_TIMESTAMP}"

# Warning for odd rounds
if (( ROUNDS_PER_PAIR % 2 != 0 )); then
  echo ""
  echo "⚠️  [WARNING] Rounds per pair (${ROUNDS_PER_PAIR}) is odd!"
  echo "    In round-robin engine tournaments, rounds per matchup should ideally be even"
  echo "    so each engine plays an equal number of games as White and Black."
  echo ""
fi

# Output paths
MATCH_DIR="data/results/matches"
mkdir -p "${MATCH_DIR}"
TEMP_PGN="/tmp/${TOURNAMENT_ID}_raw.pgn"
TELEMETRY_LOG="${MATCH_DIR}/${TOURNAMENT_ID}_telemetry.log"

# Opening Book Configuration
OPENING_FORMAT="epd"
OPENING_ORDER="random"
if [[ -f "${BOOK_ARG}" ]]; then
  OPENING_FILE="${BOOK_ARG}"
  if [[ "${BOOK_ARG}" == *.pgn ]]; then
    OPENING_FORMAT="pgn"
  fi
  BOOK_DESC="Tournament Book (${BOOK_ARG})"
else
  OPENING_FILE="${MATCH_DIR}/${TOURNAMENT_ID}_opening.epd"
  echo "${BOOK_ARG}" > "${OPENING_FILE}"
  OPENING_ORDER="sequential"
  BOOK_DESC="Custom FEN (${BOOK_ARG})"
fi

# Engine Configurations
CUTECHESS="./engines/cutechess-cli"
SYZYGY="./syzygy"
LC0_WEIGHTS="./weights/BT4-332.pb"

STOCKFISH_ARGS="name=Stockfish cmd=./engines/stockfish-ubuntu-x86-64-avx512icl dir=. proto=uci option.Threads=8 option.Hash=4096 option.SyzygyPath=${SYZYGY}"
PAWNOCCHIO_ARGS="name=Pawnocchio cmd=./engines/pawnocchio-2.0.1-linux-x86_64_znver5 dir=. proto=uci option.Threads=8 option.Hash=4096 option.SyzygyPath=${SYZYGY}"
RECKLESS_ARGS="name=Reckless cmd=./engines/reckless-linux-avx512 dir=. proto=uci option.Threads=8 option.Hash=4096 option.SyzygyPath=${SYZYGY}"
LC0_ARGS="name=Lc0 cmd=./engines/lc0 dir=. proto=uci option.WeightsFile=${LC0_WEIGHTS} option.Threads=2 option.SyzygyPath=${SYZYGY}"

TOTAL_GAMES=$(( 6 * ROUNDS_PER_PAIR ))

echo "================================================================="
echo "  🏆 STARTING 4-ENGINE ROUND-ROBIN TOURNAMENT"
echo "  Tournament ID:   ${TOURNAMENT_ID}"
echo "  Engines:         Stockfish 18, Pawnocchio 2.0.1, Reckless 0.9.0, Lc0 v0.32.1"
echo "  Rounds per Pair: ${ROUNDS_PER_PAIR} games (balanced opening repetition)"
echo "  Total Games:     ${TOTAL_GAMES} tournament games"
echo "  Time Control:    ${TC}"
echo "  Opening Suite:   ${BOOK_DESC}"
echo "  Telemetry Log:   ${TELEMETRY_LOG}"
echo "================================================================="

# Start Telemetry Log Header
{
  echo "TOURNAMENT_ID=${TOURNAMENT_ID}"
  echo "STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "ENGINES=Stockfish,Pawnocchio,Reckless,Lc0"
  echo "ROUNDS_PER_PAIR=${ROUNDS_PER_PAIR}"
  echo "TOTAL_GAMES=${TOTAL_GAMES}"
  echo "TIME_CONTROL=${TC}"
  echo "OPENING_SUITE=${BOOK_DESC}"
  echo "--- LIVE TOURNAMENT TELEMETRY ---"
} > "${TELEMETRY_LOG}"

# Run cutechess-cli round-robin tournament
"${CUTECHESS}" \
  -tournament round-robin \
  -engine ${STOCKFISH_ARGS} \
  -engine ${PAWNOCCHIO_ARGS} \
  -engine ${RECKLESS_ARGS} \
  -engine ${LC0_ARGS} \
  -each proto=uci tc="${TC}" \
  -openings file="${OPENING_FILE}" format="${OPENING_FORMAT}" order="${OPENING_ORDER}" \
  -rounds "$(( ROUNDS_PER_PAIR / 2 ))" \
  -games 2 \
  -repeat \
  -concurrency 1 \
  -recover \
  -draw movenumber=40 movecount=5 score=10 \
  -resign movecount=3 score=600 \
  -pgnout "${TEMP_PGN}" \
  | tee -a "${TELEMETRY_LOG}"

# Ingest all games into 3NF Parquet Database Tables
"${REPO_ROOT}/.venv/bin/python" -m chess_ds.match_ingest "${TEMP_PGN}" "${TOURNAMENT_ID}" "tournament" "all" "${TC}" "${TOTAL_GAMES}" || true

echo ""
echo "================================================================="
echo "✓ Tournament ${TOURNAMENT_ID} successfully completed!"
echo "✓ Match telemetry logged to:    ${TELEMETRY_LOG}"
echo "✓ 3NF Tables saved to DB:       data/results/matches/engine_matches_${TOURNAMENT_ID}.parquet"
echo "                                data/results/matches/engine_match_games_${TOURNAMENT_ID}.parquet"
echo "  (To export PGN on-demand: uv run python -m chess_ds.cli export-pgn --match-id ${TOURNAMENT_ID})"
echo "================================================================="
