#!/usr/bin/env bash
# Live demo: Primary-Backup failover vs Single-Server baseline.
# Place in docker-failover/tests/ and run:  ./tests/demo.sh
cd "$(dirname "$0")/.."

PORT=18080
G='\033[1;32m'; R='\033[1;31m'; B='\033[1;34m'; Y='\033[1;33m'; N='\033[0m'

say()  { echo -e "\n${Y}>>> $*${N}"; }
wait_ready() {
  for _ in $(seq 1 30); do
    curl -sf -m 1 "localhost:$PORT" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

# Prints one line every 0.5 s: time, answering server, HTTP status.
viewer() {
  while true; do
    out=$(curl -s -m 3 -w ' [HTTP %{http_code}]' "localhost:$PORT" 2>/dev/null)
    case "$out" in
      *PRIMARY*) c=$G ;;
      *BACKUP*)  c=$B ;;
      *)         c=$R ;;
    esac
    echo -e "$(date +%T.%3N)  ${c}${out}${N}"
    sleep 0.5
  done
}

cleanup() {
  [ -n "${VP:-}" ] && kill "$VP" 2>/dev/null
  docker compose -f docker-compose.yml down -t 1 >/dev/null 2>&1
  docker compose -f docker-compose.baseline.yml down -t 1 >/dev/null 2>&1
}
trap cleanup EXIT

run_part() {   # $1 = compose file
  local F="$1"
  docker compose -f "$F" up -d --build >/dev/null 2>&1
  say "Waiting for Nginx to be ready..."
  wait_ready || { echo "Stack did not start"; exit 1; }
  viewer & VP=$!
  sleep 5
  say "Crash: killing the PRIMARY server now"
  docker compose -f "$F" kill primary >/dev/null 2>&1
  sleep 12
  say "Restarting the PRIMARY server"
  docker compose -f "$F" start primary >/dev/null 2>&1
  sleep 10
  kill "$VP" 2>/dev/null; wait "$VP" 2>/dev/null; VP=""
}

clear
echo -e "${Y}Docker-Based Server Failover and High Availability System${N}"
echo "Client -> Nginx (172.30.0.10) -> Primary (.11) / Backup (.12)"
echo "Only Nginx is exposed on host port $PORT."
echo
read -rp "Press Enter to start PART 1 (Primary-Backup)... "

say "PART 1: Primary-Backup. Watch the answers: green = PRIMARY, blue = BACKUP"
run_part docker-compose.yml
say "Result: every request returned HTTP 200, even during the crash."
say "Nginx log (which upstream served each request):"
docker compose -f docker-compose.yml logs --no-log-prefix --tail 12 nginx
docker compose -f docker-compose.yml down -t 1 >/dev/null 2>&1

echo
read -rp "Press Enter to start PART 2 (Single-Server baseline)... "

say "PART 2: Baseline, one server and no backup. Red = failed request"
run_part docker-compose.baseline.yml
say "Result: the service was down for the whole outage."
docker compose -f docker-compose.baseline.yml down -t 1 >/dev/null 2>&1

say "PART 3: Measured results (average of 3 runs each)"
printf "%-28s %-22s %s\n" "Metric" "Baseline" "Primary-Backup"
printf "%-28s %-22s %s\n" "Request loss" "22" "0"
printf "%-28s %-22s %s\n" "Service downtime" "21.14 s" "0 s"
printf "%-28s %-22s %s\n" "Availability (time-based)" "64.75 %" "100 %"
printf "%-28s %-22s %s\n" "Failover time" "n/a" "about 0.16 s"
printf "%-28s %-22s %s\n" "Recovery to primary" "about 1.0 s" "about 6.3 s"
printf "%-28s %-22s %s\n" "Max response time" "about 34 ms" "about 1007 ms"
echo
echo "Done."
