#!/usr/bin/env python3
"""On-chain forensics for the Trezor phishing harvest address.

Pulls the complete tx history from mempool.space (paginated), separates
deposits (victim payments) from sweeps (attacker cash-out), values each
deposit at its own block time using historical BTC/USD, and maps the
downstream consolidation addresses.
"""
import json
import os
import sys
import time
import urllib.request

API = "https://mempool.space/api"
ADDR = sys.argv[1] if len(sys.argv) > 1 else "bc1qrz33mr7tx8wrpcs2pxrvv83hqwpm907s9shkz4"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/root/workspace/trezor-ads-teardown/data"


def get(url, tries=4, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(2 + i * 3)
    raise RuntimeError(f"GET {url} failed: {last!r}")


def all_txs(addr):
    """Paginate the full chain history (mempool.space returns 25/page)."""
    txs, last_txid = [], None
    while True:
        url = f"{API}/address/{addr}/txs"
        if last_txid:
            url += f"/chain/{last_txid}"
        page = get(url)
        if not page:
            break
        txs.extend(page)
        last_txid = page[-1]["txid"]
        print(f"  fetched {len(txs)} txs...", file=sys.stderr)
        if len(page) < 25:
            break
        time.sleep(0.7)
    return txs


PRICE_CACHE = {}


def usd_at(ts):
    """Historical BTC/USD near a timestamp, from mempool.space price history."""
    bucket = ts - (ts % 3600)
    if bucket in PRICE_CACHE:
        return PRICE_CACHE[bucket]
    try:
        d = get(f"{API}/v1/historical-price?currency=USD&timestamp={ts}")
        p = None
        if isinstance(d, dict):
            prices = d.get("prices") or []
            if prices:
                p = prices[0].get("USD")
            elif d.get("USD"):
                p = d["USD"]
        PRICE_CACHE[bucket] = p
        return p
    except Exception:
        PRICE_CACHE[bucket] = None
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"[*] address {ADDR}", file=sys.stderr)
    stats = get(f"{API}/address/{ADDR}")
    txs = all_txs(ADDR)
    print(f"[*] total txs {len(txs)}", file=sys.stderr)

    deposits, sweeps = [], []
    counterparties = {}
    for t in txs:
        ts = t.get("status", {}).get("block_time")
        h = t.get("status", {}).get("block_height")
        vin_has = any((i.get("prevout") or {}).get("scriptpubkey_address") == ADDR for i in t.get("vin", []))
        recv = sum(o["value"] for o in t.get("vout", [])
                   if o.get("scriptpubkey_address") == ADDR)
        sent_out = sum(o["value"] for o in t.get("vout", [])
                       if o.get("scriptpubkey_address") != ADDR)
        if vin_has:
            # attacker spending from the harvest address
            dests = [(o.get("scriptpubkey_address"), o["value"]) for o in t.get("vout", [])
                     if o.get("scriptpubkey_address") != ADDR]
            for a, v in dests:
                if a:
                    counterparties[a] = counterparties.get(a, 0) + v
            sweeps.append({"txid": t["txid"], "time": ts, "height": h,
                           "sent_sats": sent_out, "dests": dests})
        elif recv:
            senders = sorted({(i.get("prevout") or {}).get("scriptpubkey_address")
                              for i in t.get("vin", []) if (i.get("prevout") or {}).get("scriptpubkey_address")})
            deposits.append({"txid": t["txid"], "time": ts, "height": h,
                             "sats": recv, "btc": recv / 1e8, "senders": senders})

    deposits.sort(key=lambda d: d["time"] or 0)
    sweeps.sort(key=lambda d: d["time"] or 0)

    print(f"[*] pricing {len(deposits)} deposits...", file=sys.stderr)
    total_usd = 0.0
    for d in deposits:
        if d["time"]:
            p = usd_at(d["time"])
            d["btc_usd_at_time"] = p
            d["usd"] = round(d["btc"] * p, 2) if p else None
            if d["usd"]:
                total_usd += d["usd"]
            time.sleep(0.25)

    def iso(ts):
        return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts)) if ts else None

    report = {
        "address": ADDR,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain_stats": stats.get("chain_stats"),
        "total_received_btc": stats["chain_stats"]["funded_txo_sum"] / 1e8,
        "total_sent_btc": stats["chain_stats"]["spent_txo_sum"] / 1e8,
        "balance_btc": (stats["chain_stats"]["funded_txo_sum"] - stats["chain_stats"]["spent_txo_sum"]) / 1e8,
        "deposit_count": len(deposits),
        "sweep_count": len(sweeps),
        "total_deposit_usd_at_receipt": round(total_usd, 2),
        "first_deposit": iso(deposits[0]["time"]) if deposits else None,
        "last_deposit": iso(deposits[-1]["time"]) if deposits else None,
        "first_sweep": iso(sweeps[0]["time"]) if sweeps else None,
        "last_sweep": iso(sweeps[-1]["time"]) if sweeps else None,
        "largest_deposit": max(deposits, key=lambda d: d["sats"]) if deposits else None,
        "top_counterparties": sorted(
            [{"address": a, "sats": v, "btc": v / 1e8} for a, v in counterparties.items()],
            key=lambda x: -x["sats"])[:25],
        "deposits": deposits,
        "sweeps": sweeps,
    }
    with open(os.path.join(OUT, "btc_forensics.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps({k: report[k] for k in
                      ("address", "total_received_btc", "balance_btc", "deposit_count",
                       "sweep_count", "total_deposit_usd_at_receipt", "first_deposit",
                       "last_deposit", "first_sweep", "last_sweep")}, indent=2))
    print("\nTop counterparties:")
    for c in report["top_counterparties"][:10]:
        print(f"  {c['address']}  {c['btc']:.8f} BTC")


if __name__ == "__main__":
    main()
