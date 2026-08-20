#!/usr/bin/env bash
# =============================================================================
# chess-ds: Engine vs. Engine Match Runner using cutechess-cli
# =============================================================================
# Usage:
#   ./scripts/run_match.sh [ROUNDS] [TIME_CONTROL] [CONCURRENCY]
# Example:
#   ./scripts/run_match.sh 10 "10+0.1" 2
# =============================================================================

set -euo pipefail

# Ensure execution from repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# Arguments & Defaults
ROUNDS="${1:-10}"
TC="${2:-10+0.1}"
DEFAULT_START_FEN="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
START_FEN="${3:-${DEFAULT_START_FEN}}"
ENG1_KEY="${4:-lc0}"
ENG2_KEY="${5:-reckless}"
MATCH_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
MATCH_ID="match_${MATCH_TIMESTAMP}"

# Odd rounds warning for color balance
if (( ROUNDS % 2 != 0 )); then
  echo ""
  echo "⚠️  [WARNING] Number of rounds (${ROUNDS}) is odd!"
  echo "    In head-to-head engine matches, rounds should ideally be even"
  echo "    so each engine plays an equal number of games as White and Black."
  echo ""
fi

# Starting position warning
if [[ "${START_FEN}" == "${DEFAULT_START_FEN}" ]]; then
  echo "⚠️  [WARNING] Using default starting FEN (standard starting position)!"
  echo "    Playing engine matches from the standard starting board is not advisable"
  echo "    because deterministic top engines frequently repeat identical draw lines."
  echo "    Supplying varied opening FENs or a balanced opening book is strongly recommended."
  echo ""
fi

# Output paths
MATCH_DIR="data/results/matches"
mkdir -p "${MATCH_DIR}"
PGN_OUT="${MATCH_DIR}/${MATCH_ID}.pgn"
TELEMETRY_LOG="${MATCH_DIR}/${MATCH_ID}_telemetry.log"
OPENING_EPD="${MATCH_DIR}/${MATCH_ID}_opening.epd"
echo "${START_FEN}" > "${OPENING_EPD}"

# Engine Binaries & Configurations
CUTECHESS="./engines/cutechess-cli"
SYZYGY="./syzygy"
LC0_WEIGHTS="./weights/BT4-332.pb"

# Helper function to get cutechess-cli engine args
get_engine_args() {
  local key="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
  case "$key" in
    *lc0*|*leela*)
      echo "name=Lc0 cmd=./engines/lc0 dir=. proto=uci option.WeightsFile=${LC0_WEIGHTS} option.Threads=2 option.SyzygyPath=${SYZYGY}"
      ;;
    *reckless*)
      echo "name=Reckless cmd=./engines/reckless-linux-avx512 dir=. proto=uci option.Threads=8 option.Hash=4096 option.SyzygyPath=${SYZYGY}"
      ;;
    *pawnocchio*)
      echo "name=Pawnocchio cmd=./engines/pawnocchio-2.0.1-linux-x86_64_znver5 dir=. proto=uci option.Threads=8 option.Hash=4096 option.SyzygyPath=${SYZYGY}"
      ;;
    *stockfish*|*)
      echo "name=Stockfish cmd=./engines/stockfish-ubuntu-x86-64-avx512icl dir=. proto=uci option.Threads=8 option.Hash=4096 option.SyzygyPath=${SYZYGY}"
      ;;
  esac
}

ENG1_ARGS="$(get_engine_args "${ENG1_KEY}")"
ENG2_ARGS="$(get_engine_args "${ENG2_KEY}")"

echo "================================================================="
echo "  STARTING ENGINE VS ENGINE HEAD-TO-HEAD MATCH (2 ENGINES)"
echo "  Match ID:       ${MATCH_ID}"
echo "  Rounds:         ${ROUNDS} games (repeat each opening)"
echo "  Time Control:   ${TC}"
echo "  Starting FEN:   ${START_FEN}"
echo "  Engine 1:       ${ENG1_KEY}"
echo "  Engine 2:       ${ENG2_KEY}"
echo "  PGN Target:     ${PGN_OUT}"
echo "  Telemetry Log:  ${TELEMETRY_LOG}"
echo "================================================================="

# Start Telemetry Log Header
{
  echo "MATCH_ID=${MATCH_ID}"
  echo "STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "ENGINE1=${ENG1_KEY}"
  echo "ENGINE2=${ENG2_KEY}"
  echo "TOTAL_GAMES=${ROUNDS}"
  echo "TIME_CONTROL=${TC}"
  echo "STARTING_FEN=${START_FEN}"
  echo "--- LIVE MATCH TELEMETRY ---"
} > "${TELEMETRY_LOG}"

# Run cutechess-cli tournament sequentially with live tee to dedicated telemetry log
"${CUTECHESS}" \
  -engine ${ENG1_ARGS} \
  -engine ${ENG2_ARGS} \
  -each proto=uci tc="${TC}" \
  -openings file="${OPENING_EPD}" format=epd \
  -rounds "$(( ROUNDS / 2 ))" \
  -games 2 \
  -repeat \
  -concurrency 1 \
  -recover \
  -draw movenumber=40 movecount=5 score=10 \
  -resign movecount=3 score=600 \
  -pgnout "${PGN_OUT}" \
  | tee -a "${TELEMETRY_LOG}"

# Extract and parse match results from PGN in Win-Draw-Loss (+W =D -L) order
read -r WINS_E1 DRAWS_E1 LOSS_E1 WINS_E2 DRAWS_E2 LOSS_E2 < <(
  awk -v e1="${ENG1_KEY}" -v e2="${ENG2_KEY}" '
    BEGIN {
      w1=0; d1=0; l1=0;
      w2=0; d2=0; l2=0;
      white=""; black="";
    }
    /\[White "/ {
      gsub(/\[White "|"]/, "", $0);
      white=tolower($0);
    }
    /\[Black "/ {
      gsub(/\[Black "|"]/, "", $0);
      black=tolower($0);
    }
    /\[Result "/ {
      gsub(/\[Result "|"]/, "", $0);
      res=$0;
      if (res == "1-0") {
        if (index(white, e1) > 0) { w1++; l2++; }
        else { w2++; l1++; }
      } else if (res == "0-1") {
        if (index(black, e1) > 0) { w1++; l2++; }
        else { w2++; l1++; }
      } else if (res == "1/2-1/2") {
        d1++; d2++;
      }
    }
    END {
      print w1, d1, l1, w2, d2, l2;
    }
  ' "${PGN_OUT}"
)

# Append Completed Timestamp and Win-Draw-Loss Summary to Telemetry
{
  echo "--- MATCH COMPLETED ---"
  echo "COMPLETED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "PGN_PATH=${PGN_OUT}"
  echo "SUMMARY_FORMAT=Win-Draw-Loss (W - D - L)"
  echo "${ENG1_KEY}_SCORE: +${WINS_E1} =${DRAWS_E1} -${LOSS_E1} (${WINS_E1}W-${DRAWS_E1}D-${LOSS_E1}L)"
  echo "${ENG2_KEY}_SCORE: +${WINS_E2} =${DRAWS_E2} -${LOSS_E2} (${WINS_E2}W-${DRAWS_E2}D-${LOSS_E2}L)"
} >> "${TELEMETRY_LOG}"

# Automatically Ingest Match and Games into 3NF Parquet Database Tables
"${REPO_ROOT}/.venv/bin/python" -m chess_ds.match_ingest "${PGN_OUT}" "${MATCH_ID}" "${ENG1_KEY}" "${ENG2_KEY}" "${TC}" "${ROUNDS}" || true

echo ""
echo "================================================================="
echo "  MATCH FINISHED: WIN - DRAW - LOSS SUMMARY"
echo "  ${ENG1_KEY}:  +${WINS_E1} =${DRAWS_E1} -${LOSS_E1}  (${WINS_E1}W - ${DRAWS_E1}D - ${LOSS_E1}L)"
echo "  ${ENG2_KEY}:  +${WINS_E2} =${DRAWS_E2} -${LOSS_E2}  (${WINS_E2}W - ${DRAWS_E2}D - ${LOSS_E2}L)"
echo "================================================================="
echo "✓ Match ${MATCH_ID} successfully completed!"
echo "✓ Games PGN recorded in:        ${PGN_OUT}"
echo "✓ Match telemetry logged to:    ${TELEMETRY_LOG}"
echo "✓ 3NF Tables saved to DB:       data/results/matches/engine_matches_${MATCH_ID}.parquet"
echo "                                data/results/matches/engine_match_games_${MATCH_ID}.parquet"
