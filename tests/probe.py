"""Sends a request every 50 ms and logs the result to CSV.
Usage: python3 probe.py [duration_seconds] [output.csv]
"""
import csv
import json
import sys
import time
import urllib.error
import urllib.request

URL = "http://localhost:18080/"
INTERVAL = 0.05
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 60
OUT = sys.argv[2] if len(sys.argv) > 2 else "results.csv"

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "status", "server", "latency_ms"])
    end = time.time() + DURATION
    while time.time() < end:
        t0 = time.time()
        try:
            with urllib.request.urlopen(URL, timeout=3) as r:
                status = r.status
                server = json.loads(r.read().decode()).get("server", "?")
        except urllib.error.HTTPError as e:
            status, server = e.code, "NONE"
        except Exception:
            status, server = 0, "NONE"
        latency = (time.time() - t0) * 1000
        w.writerow([f"{t0:.3f}", status, server, f"{latency:.1f}"])
        f.flush()
        time.sleep(max(0, INTERVAL - (time.time() - t0)))
