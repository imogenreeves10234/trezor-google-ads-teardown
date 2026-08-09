#!/usr/bin/env python3
"""Adversarial verification of the STAR HONOUR / ledger.com / TR claim.

Tries the direct transport first; falls back to the Gonzo residential shim on 429.
Every step is paced and every negative is paired with a positive control.
"""
import json
import sys
import time

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc  # noqa: E402

OUT = {}
USE_RES = False


def post(endpoint, payload):
    global USE_RES
    if not USE_RES:
        try:
            return atc._post(endpoint, payload, retries=1, timeout=45)
        except Exception as e:
            print(f"  direct failed ({e!r}) -> switching to residential shim", file=sys.stderr)
            USE_RES = True
    import atc_res
    return atc_res._post(endpoint, payload)


def creatives(term=None, advertiser=None, region="US", pagesize=40, cursor=None):
    if advertiser:
        payload = {"2": pagesize,
                   "3": {"8": [atc.GEO[region]], "13": {"1": [advertiser]}},
                   "7": {"1": 1, "2": 0, "3": -1}}
    else:
        payload = {"2": pagesize,
                   "3": {"8": [atc.GEO[region]], "12": {"1": term, "2": True}},
                   "7": {"1": 1, "2": 0, "3": -1}}
    if cursor:
        payload["4"] = cursor
    return post("SearchService/SearchCreatives", payload)


def summarize(resp):
    rows = atc.parse_creatives(resp)
    agg = {}
    for r in rows:
        k = (r["advertiser_id"], r["advertiser_name"], r["domain"])
        agg.setdefault(k, []).append(r)
    return rows, agg


def show(label, resp):
    rows, agg = summarize(resp)
    print(f"\n### {label}: {len(rows)} creatives, {len(agg)} advertiser(s)")
    for (aid, name, dom), rs in sorted(agg.items(), key=lambda x: -len(x[1])):
        fs = [r["first_shown"] for r in rs if r["first_shown"]]
        ls = [r["last_shown"] for r in rs if r["last_shown"]]
        def d(e):
            return time.strftime('%Y-%m-%d', time.gmtime(e)) if e else '?'
        print(f"  {aid}  name={name!r}  domain={dom!r}  n={len(rs)}  "
              f"shown {d(min(fs) if fs else None)} .. {d(max(ls) if ls else None)}")
    return rows, agg


def step(fn, *a, **kw):
    time.sleep(1.2)
    for i in range(3):
        try:
            return fn(*a, **kw)
        except Exception as e:
            print(f"  retry {i+1}: {e!r}", file=sys.stderr)
            time.sleep(4 + i * 4)
    raise RuntimeError("gave up")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("all", "control"):
        r = step(creatives, term="trezor.io", region="US")
        rows, _ = show("CONTROL trezor.io US", r)
        OUT["control_us"] = len(rows)

    if which in ("all", "tr"):
        r = step(creatives, term="trezor.io", region="TR")
        rows, _ = show("CONTROL trezor.io TR", r)
        OUT["control_tr"] = len(rows)

        r = step(creatives, term="ledger.com", region="TR")
        rows, agg = show("ledger.com TR", r)
        OUT["ledger_tr"] = [dict(zip(("aid", "name", "dom", "n"), (k[0], k[1], k[2], len(v))))
                            for k, v in agg.items()]
        json.dump(rows, open("/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad/ledger_tr.json", "w"), indent=1)

    print("\n" + json.dumps(OUT, indent=1))
