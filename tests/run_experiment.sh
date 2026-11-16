#!/usr/bin/env bash
# Usage: ./tests/run_experiment.sh [proposed|baseline] [run_number]
# Timeline: 0-20s normal, kill primary at 20s, restart at 40s, end at 60s.
set -euo pipefail

MODE="${1:-proposed}"
RUN="${2:-1}"
DURATION=60
KILL_AT=20
RECOVER_AT=40

cd "$(dirname "$0")/.."

if [ "$MODE" = "baseline" ]; then
  COMPOSE="docker compose -f docker-compose.baseline.yml"
else
  COMPOSE="docker compose -f docker-compose.yml"
fi

mkdir -p results
CSV="results/${MODE}_run${RUN}.csv"
EVENTS="results/${MODE}_run${RUN}.events"

echo "[*] Starting stack ($MODE)..."
$COMPOSE up -d --build
sleep 3

echo "[*] Starting probe for ${DURATION}s -> $CSV"
python3 tests/probe.py "$DURATION" "$CSV" &
PROBE_PID=$!

sleep "$KILL_AT"
KILL_TS=$(date +%s.%N)
echo "[!] Killing primary at $KILL_TS"
$COMPOSE kill primary

sleep $((RECOVER_AT - KILL_AT))
RECOVER_TS=$(date +%s.%N)
echo "[+] Restarting primary at $RECOVER_TS"
$COMPOSE start primary

wait "$PROBE_PID"

echo "kill=$KILL_TS" > "$EVENTS"
echo "recover=$RECOVER_TS" >> "$EVENTS"

$COMPOSE logs nginx > "results/${MODE}_run${RUN}.nginx.log" 2>&1 || true

echo "[*] Tearing down"
$COMPOSE down

echo "[OK] Done. Analyze with:"
echo "     python3 tests/analyze.py $CSV $EVENTS"
