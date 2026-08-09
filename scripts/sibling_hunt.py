#!/usr/bin/env python3
"""Sibling hunt: enumerate sites.google.com crypto-phishing pages beyond the 10 brands
already covered. urlscan.io search, paginated, with 429 backoff."""
import json, sys, time, urllib.parse, urllib.request, os

OUT = "/root/workspace/trezor-ads-teardown/data"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
API = "https://urlscan.io/api/v1/search/"

STATS = {"req": 0, "429": 0, "err": 0}


def get(url, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=45) as f:
                STATS["req"] += 1
                return json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                STATS["429"] += 1
                wait = min(120, 8 * (i + 1))
                print(f"    429, sleep {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            STATS["err"] += 1
            print(f"    HTTP {e.code} on {url[:110]}", file=sys.stderr)
            return None
        except Exception as e:
            STATS["err"] += 1
            print(f"    ERR {e} ", file=sys.stderr)
            time.sleep(5)
    return None


def search(q, maxpages=12):
    """Full paginated search. Returns list of result dicts. None on hard failure."""
    out, after, pages, failed = [], None, 0, False
    while pages < maxpages:
        u = API + "?q=" + urllib.parse.quote(q) + "&size=100"
        if after:
            u += "&search_after=" + urllib.parse.quote(after)
        d = get(u)
        if d is None:
            failed = True
            break
        res = d.get("results", [])
        out.extend(res)
        pages += 1
        if len(res) < 100:
            break
        s = res[-1].get("sort")
        if not s:
            break
        after = ",".join(str(x) for x in s)
        time.sleep(2.5)
    return out, failed


def main():
    terms = json.load(open(sys.argv[1]))
    label = sys.argv[2]
    all_rows, meta = [], []
    for t in terms:
        q = t["q"]
        print(f"[{t['name']}] {q}", file=sys.stderr)
        res, failed = search(q)
        meta.append({"name": t["name"], "q": q, "n": len(res), "failed": failed})
        for r in res:
            all_rows.append({
                "term": t["name"],
                "url": (r.get("page") or {}).get("url") or (r.get("task") or {}).get("url"),
                "task_url": (r.get("task") or {}).get("url"),
                "time": (r.get("task") or {}).get("time"),
                "uuid": r.get("_id"),
                "title": (r.get("page") or {}).get("title"),
                "domain": (r.get("page") or {}).get("domain"),
            })
        print(f"    -> {len(res)}{' [FAILED/partial]' if failed else ''}", file=sys.stderr)
        time.sleep(2.5)
    json.dump({"meta": meta, "rows": all_rows, "stats": STATS},
              open(f"{OUT}/sibling_{label}.json", "w"), indent=1)
    print(json.dumps({"terms": len(terms), "rows": len(all_rows), "stats": STATS}), file=sys.stderr)


if __name__ == "__main__":
    main()
