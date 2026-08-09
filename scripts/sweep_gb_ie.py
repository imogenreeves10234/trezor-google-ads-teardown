#!/usr/bin/env python3
"""Sweep GB + IE for crypto-wallet impersonation ads via the existing ATC client."""
import json
import os
import sys
import time

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc_curl  # noqa: F401  (patches atc._post onto curl)
import atc  # noqa: E402

OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
os.makedirs(OUT, exist_ok=True)

GOOGLE_HOSTS = [
    "sites.google.com", "script.google.com", "docs.google.com", "drive.google.com",
    "groups.google.com", "lookerstudio.google.com", "datastudio.google.com",
    "firebaseapp.com", "web.app", "appspot.com", "blogspot.com",
    "googleusercontent.com", "storage.googleapis.com", "translate.goog", "google.com",
]
BRANDS = [
    "trezor.io", "ledger.com", "exodus.com", "metamask.io", "phantom.app",
    "uniswap.org", "tangem.com", "keepkey.com", "bitbox.swiss", "safepal.com",
    "ellipal.com", "coinbase.com", "kraken.com", "binance.com", "electrum.org",
    "blockchain.com", "ledger.io", "trezor.com",
]
TERMS = ["trezor", "trezor suite", "ledger live", "ledger wallet", "metamask",
         "exodus wallet", "phantom wallet", "hardware wallet", "crypto wallet",
         "seed phrase", "wallet recovery"]


def paged(fn, key, region, max_pages):
    """Collect creatives across pages. Returns (rows, pages, error_or_None)."""
    rows, cursor, err = [], None, None
    for _ in range(max_pages):
        try:
            r = fn(key, region, cursor=cursor) if cursor else fn(key, region)
        except Exception as e:
            err = str(e)[:200]
            break
        rows.extend(atc.parse_creatives(r))
        cursor = r.get("2")
        if not cursor or not r.get("1"):
            break
    return rows, err


def run(region):
    res = {"region": region, "control": None, "domains": {}, "suggest": {}}

    ctrl, err = paged(atc.search_creatives, "trezor.io", region, 5)
    res["control"] = {"count": len(ctrl), "error": err,
                      "has_trezor_co": any(r["advertiser_id"] == "AR07426507167890407425" for r in ctrl)}
    res["domains"]["trezor.io"] = ctrl
    print(f"[{region}] CONTROL trezor.io -> {len(ctrl)} creatives err={err}", flush=True)

    for d in GOOGLE_HOSTS + [b for b in BRANDS if b != "trezor.io"]:
        pages = 3 if d in GOOGLE_HOSTS else 5
        rows, err = paged(atc.search_creatives, d, region, pages)
        res["domains"][d] = rows
        advs = {(r["advertiser_name"], r["domain"], r["advertiser_id"]) for r in rows}
        print(f"[{region}] {d:28s} {len(rows):4d} creatives  {len(advs)} advertisers  err={err}", flush=True)
        for a in sorted(advs, key=lambda x: str(x[0])):
            print(f"        - {a[0]} | {a[1]} | {a[2]}", flush=True)

    for t in TERMS:
        try:
            s = atc.suggestions(t, region)
        except Exception as e:
            s = {"_error": str(e)[:200]}
        res["suggest"][t] = s
        print(f"[{region}] suggest {t!r} -> {json.dumps(s, ensure_ascii=False)[:400]}", flush=True)

    json.dump(res, open(f"{OUT}/sweep_{region}.json", "w"), ensure_ascii=False)
    return res


if __name__ == "__main__":
    for reg in sys.argv[1:] or ["GB", "IE"]:
        run(reg)
        time.sleep(2)
