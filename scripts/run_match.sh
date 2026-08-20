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
CONCURRENCY="${3:-2}"
MATCH_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
MATCH_ID="match_${MATCH_TIMESTAMP}"

# Output paths
MATCH_DIR="data/results/matches"
mkdir -p "${MATCH_DIR}"
PGN_OUT="${MATCH_DIR}/${MATCH_ID}.pgn"
TELEMETRY_LOG="${MATCH_DIR}/${MATCH_ID}_telemetry.log"
TELEMETRY_SUMMARY="${MATCH_DIR}/${MATCH_ID}_summary.txt"

# Engine Binaries
CUTECHESS="./engines/cutechess-cli"
STOCKFISH="./engines/stockfish-ubuntu-x86-64-avx512icl"
LC0="./engines/lc0"
LC0_WEIGHTS="./weights/BT4-332.pb"
SYZYGY="./syzygy"

echo "================================================================="
echo "  STARTING ENGINE VS ENGINE HEAD-TO-HEAD MATCH"
echo "  Match ID:       ${MATCH_ID}"
echo "  Rounds:         ${ROUNDS} games"
echo "  Time Control:   ${TC}"
echo "  Concurrency:    ${CONCURRENCY}"
echo "  Engine 1:       Stockfish 18 (AVX-512 CPU)"
echo "  Engine 2:       Lc0 v0.32.1 (RTX 5090 GPU)"
echo "  PGN Target:     ${PGN_OUT}"
echo "  Telemetry Log:  ${TELEMETRY_LOG}"
echo "================================================================="

# Start Telemetry Log Header
{
  echo "MATCH_ID=${MATCH_ID}"
  echo "STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "ENGINE1=Stockfish 18"
  echo "ENGINE2=Lc0 v0.32.1"
  echo "ROUNDS=${ROUNDS}"
  echo "TIME_CONTROL=${TC}"
  echo "CONCURRENCY=${CONCURRENCY}"
  echo "--- LIVE MATCH TELEMETRY ---"
} > "${TELEMETRY_LOG}"

# Run cutechess-cli tournament with live tee to dedicated telemetry log
"${CUTECHESS}" \
  -engine name="Stockfish 18" cmd="${STOCKFISH}" proto=uci option.Threads=4 option.Hash=2048 option.SyzygyPath="${SYZYGY}" \
  -engine name="Lc0 v0.32.1" cmd="${LC0}" proto=uci arg="--weights=${LC0_WEIGHTS}" arg="--threads=2" option.SyzygyPath="${SYZYGY}" \
  -each proto=uci tc="${TC}" \
  -rounds "${ROUNDS}" \
  -games 2 \
  -repeat \
  -concurrency "${CONCURRENCY}" \
  -draw movenumber=40 movecount=5 score=10 \
  -resign movecount=3 score=600 \
  -pgnout "${PGN_OUT}" \
  -outcome \
  | tee -a "${TELEMETRY_LOG}"

# Append Completed Timestamp and Summary to Telemetry
{
  echo "--- MATCH COMPLETED ---"
  echo "COMPLETED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "PGN_PATH=${PGN_OUT}"
} >> "${TELEMETRY_LOG}"

echo ""
echo "✓ Match ${MATCH_ID} successfully completed!"
echo "✓ Games PGN recorded in:     ${PGN_OUT}"
echo "✓ Match telemetry logged to: ${TELEMETRY_LOG}"
