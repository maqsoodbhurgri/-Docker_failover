"""Computes project metrics from a probe CSV + events file.
Usage: python3 analyze.py results/proposed_run1.csv results/proposed_run1.events
Optional chart: pip install matplotlib
"""
import csv
import statistics
import sys

csv_path, events_path = sys.argv[1], sys.argv[2]

events = {}
with open(events_path) as f:
    for line in f:
        k, v = line.strip().split("=")
        events[k] = float(v)
kill, recover = events["kill"], events["recover"]

rows = []
with open(csv_path) as f:
    for r in csv.DictReader(f):
        rows.append({
            "t": float(r["timestamp"]),
            "status": int(r["status"]),
            "server": r["server"],
            "lat": float(r["latency_ms"]),
        })

total = len(rows)
ok = [r for r in rows if r["status"] == 200]
failed = [r for r in rows if r["status"] != 200]


def pct(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * p))] if s else float("nan")


after_kill = [r for r in rows if r["t"] >= kill]

# Detection: kill -> first sign of failure (error or non-PRIMARY response)
first_sign = next((r for r in after_kill
                   if r["status"] != 200 or r["server"] != "PRIMARY"), None)
detection = (first_sign["t"] - kill) if first_sign else None

# Failover: kill -> first successful BACKUP response
first_backup = next((r for r in after_kill
                     if r["status"] == 200 and r["server"] == "BACKUP"), None)
failover = (first_backup["t"] + first_backup["lat"] / 1000 - kill) if first_backup else None

# Downtime: first failed request after kill -> next successful response
downtime = 0.0
first_fail = next((r for r in after_kill if r["status"] != 200), None)
if first_fail:
    next_ok = next((r for r in after_kill
                    if r["t"] > first_fail["t"] and r["status"] == 200), None)
    downtime = (next_ok["t"] - first_fail["t"]) if next_ok else (rows[-1]["t"] - first_fail["t"])

# Recovery: primary restart -> first PRIMARY response again
back = next((r for r in rows if r["t"] >= recover
             and r["status"] == 200 and r["server"] == "PRIMARY"), None)
recovery = (back["t"] - recover) if back else None

lat = [r["lat"] for r in ok]
availability = 100.0 * len(ok) / total if total else 0.0


def fmt(v):
    return "N/A" if v is None else f"{v:.3f} s"


print("=" * 50)
print(f"File: {csv_path}")
print("=" * 50)
print(f"Total requests         : {total}")
print(f"Successful             : {len(ok)}")
print(f"Request loss           : {len(failed)}")
print(f"Request success rate   : {availability:.2f} %")
print(f"Service availability   : {availability:.2f} %")
print(f"Failure detection time : {fmt(detection)}")
print(f"Failover time          : {fmt(failover)}")
print(f"Service downtime       : {downtime:.3f} s")
print(f"Recovery (back to PRIMARY): {fmt(recovery)}")
if lat:
    print(f"Response time mean     : {statistics.mean(lat):.1f} ms")
    print(f"Response time median   : {statistics.median(lat):.1f} ms")
    print(f"Response time p95      : {pct(lat, 0.95):.1f} ms")
    print(f"Response time max      : {max(lat):.1f} ms")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t0 = rows[0]["t"]
    colors = {"PRIMARY": "tab:green", "BACKUP": "tab:blue", "NONE": "tab:red"}
    plt.figure(figsize=(10, 4))
    for name, c in colors.items():
        pts = [(r["t"] - t0, r["lat"]) for r in rows if r["server"] == name]
        if pts:
            plt.scatter(*zip(*pts), s=6, c=c, label=name)
    plt.axvline(kill - t0, color="k", linestyle="--", label="primary killed")
    plt.axvline(recover - t0, color="gray", linestyle="--", label="primary restarted")
    plt.xlabel("Time (s)")
    plt.ylabel("Latency (ms)")
    plt.title("Request latency and serving node over time")
    plt.legend()
    plt.tight_layout()
    out = csv_path.replace(".csv", ".png")
    plt.savefig(out, dpi=150)
    print(f"Chart saved            : {out}")
except ImportError:
    print("(Optional: pip install matplotlib to also get a chart)")
