#!/usr/bin/env python3
"""Run the SERP probe across many geo x query pairs under a hard concurrency cap.

Each probe launches a headful Chrome through a residential exit; this box has
14 GB RAM and NO swap, so concurrency is capped at 4 to stay clear of the OOM
killer that has killed sessions here before.
"""
import itertools
import json
import os
import subprocess
import sys
import threading
import time
from queue import Queue

ROOT = "/root/workspace/trezor-ads-teardown"
OUTDIR = os.path.join(ROOT, "geo")
MAXPAR = int(os.environ.get("MAXPAR", "4"))
TRIES = int(os.environ.get("TRIES", "5"))

# tld/hl per geo so the SERP is the one a local user actually sees
GEOS = [
    ("US", "com", "en"), ("GB", "co.uk", "en"), ("DE", "de", "de"),
    ("FR", "fr", "fr"), ("NL", "nl", "nl"), ("CZ", "cz", "cs"),
    ("PL", "pl", "pl"), ("ES", "es", "es"), ("IT", "it", "it"),
    ("CA", "ca", "en"), ("AU", "com.au", "en"), ("IN", "co.in", "en"),
    ("BR", "com.br", "pt"), ("TR", "com.tr", "tr"), ("AE", "ae", "en"),
    ("SG", "com.sg", "en"), ("ZA", "co.za", "en"), ("MX", "com.mx", "es"),
]
QUERIES = ["trezor wallet", "trezor suite", "trezor login"]


def worker(q, results, lock):
    while True:
        try:
            cc, tld, hl, query = q.get_nowait()
        except Exception:
            return
        tag = f"{cc}/{query}"
        try:
            p = subprocess.run(
                ["xvfb-run", "-a", "--server-args=-screen 0 1920x1080x24",
                 "python3", "-u", os.path.join(ROOT, "scripts", "serp_probe.py"),
                 cc, query, OUTDIR, tld, hl, str(TRIES)],
                capture_output=True, text=True, timeout=1800, cwd=ROOT)
            last = [l for l in p.stdout.strip().splitlines() if l.startswith("{")]
            res = json.loads(last[-1]) if last else {"cc": cc, "q": query, "status": "NO_OUTPUT"}
        except subprocess.TimeoutExpired:
            res = {"cc": cc, "q": query, "status": "TIMEOUT"}
        except Exception as e:
            res = {"cc": cc, "q": query, "status": "ERROR", "err": repr(e)[:200]}
        with lock:
            results.append(res)
            print(f"[{len(results)}] {tag:28} -> {res.get('status')} ads={res.get('ads')}", flush=True)
        q.task_done()


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    only = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "all" else None
    queries = sys.argv[2].split("|") if len(sys.argv) > 2 else QUERIES
    q = Queue()
    n = 0
    for (cc, tld, hl), query in itertools.product(GEOS, queries):
        if only and cc not in only:
            continue
        q.put((cc, tld, hl, query)); n += 1
    print(f"[*] {n} probes, {MAXPAR} parallel, {TRIES} tries each", flush=True)
    results, lock = [], threading.Lock()
    ts = [threading.Thread(target=worker, args=(q, results, lock), daemon=True) for _ in range(MAXPAR)]
    t0 = time.time()
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"[*] done in {(time.time()-t0)/60:.1f} min", flush=True)
    with open(os.path.join(ROOT, "data", "fleet_summary.json"), "w") as f:
        json.dump(results, f, indent=2)
    ok = [r for r in results if r.get("status") == "OK"]
    print(f"[*] verified SERPs: {len(ok)}/{len(results)}")


if __name__ == "__main__":
    main()
