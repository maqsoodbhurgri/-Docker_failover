# Docker-Based Server Failover and High Availability System

Term project for CSCN513 - Computer Networks, Sindh University Laar Campus Badin.
Authors: Maqsood Ahmed (2K24/BLCS/31), Aijaz Ali (2K24/BLCS/06).
Supervisor: Prof Dileep Kumar.

## Overview
A containerized Primary-Backup architecture. An Nginx reverse proxy forwards
client requests over a Docker bridge network to a Primary Flask server. When the
Primary fails, Nginx retries the request on the Backup server, so clients
keep getting responses. A Single-Server setup is used as the baseline.

    Client -> Nginx (172.30.0.10) -> Primary (172.30.0.11)
                                  -> Backup  (172.30.0.12)

Only Nginx publishes a host port (18080). The backends are reachable only inside
the Docker network.

## Requirements
- Linux (tested on Ubuntu), Docker with the Compose plugin, Python 3
- Optional: matplotlib (`sudo apt install python3-matplotlib`) for charts

## Quick start
    docker compose up -d --build
    curl localhost:18080                # PRIMARY
    docker compose kill primary
    curl localhost:18080                # BACKUP
    docker compose start primary
    sleep 6 && curl localhost:18080     # PRIMARY again
    docker compose down

## Run the experiments
Each run lasts 60 s: primary killed at 20 s, restarted at 40 s.

    ./tests/run_experiment.sh baseline 1
    python3 tests/analyze.py results/baseline_run1.csv results/baseline_run1.events

    ./tests/run_experiment.sh proposed 1
    python3 tests/analyze.py results/proposed_run1.csv results/proposed_run1.events

Run baseline and proposed one at a time (they share host port 18080).

## Results (3 runs each)
| Metric | Baseline (single server) | Proposed (primary-backup) |
|---|---|---|
| Request loss | 22 | 0 |
| Service downtime | 21.14 s | 0 s |
| Time-based availability | 64.75 % | 100 % |
| Failover time | N/A | about 0.16 s |
| Recovery to primary after restart | about 1.0 s | about 6.3 s |
| Max response time | about 34 ms | about 1007 ms |

Notes:
- Open-source Nginx uses passive health checks (max_fails / fail_timeout).
  While the primary is down, one request about every 7 s pays a 1 s
  connect-timeout penalty before being retried on the backup. No request fails.
- Recovery is slower in the proposed setup because Nginx waits for
  fail_timeout (5 s) before probing the primary again.
- Failover time includes the delay of the kill command and the 50 ms probe
  interval, so it is an upper-bound estimate.

## Project layout
- backend/   Flask service and Dockerfile
- nginx/     nginx.conf (primary-backup), nginx.baseline.conf (single server)
- tests/     probe.py, run_experiment.sh, analyze.py
- results/   CSV logs, event timestamps, charts
- docker-compose.yml, docker-compose.baseline.yml
