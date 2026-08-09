#!/usr/bin/env python3
"""Resumable, slow urlscan sweep. Appends one JSON line per term to <out>.jsonl.
Re-running skips terms already present, so it survives a rate-limit wall."""
import json, os, sys, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
API = "https://urlscan.io/api/v1/search/"


def get(url, tries=6):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=45) as f:
                return json.loads(f.read().decode()), None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 70 + 50 * i
                print(f"    429 -> sleep {w}s", file=sys.stderr, flush=True)
                time.sleep(w)
                continue
            return None, "HTTP%d" % e.code
        except Exception:
            time.sleep(10)
    return None, "RATELIMIT"


def search(q):
    out, after, err = [], None, None
    while True:
        u = API + "?q=" + urllib.parse.quote(q) + "&size=100"
        if after:
            u += "&search_after=" + urllib.parse.quote(after)
        d, err = get(u)
        if d is None:
            break
        res = d.get("results", [])
        out.extend(res)
        if len(res) < 100:
            break
        s = res[-1].get("sort")
        if not s:
            break
        after = ",".join(str(x) for x in s)
        time.sleep(8)
    return out, err


def main():
    terms = json.load(open(sys.argv[1]))
    outp = sys.argv[2]
    done = set()
    if os.path.exists(outp):
        for l in open(outp):
            try:
                done.add(json.loads(l)["name"])
            except Exception:
                pass
    fh = open(outp, "a")
    for t in terms:
        if t["name"] in done:
            continue
        print("[%s]" % t["name"], file=sys.stderr, flush=True)
        res, err = search(t["q"])
        rows = [{"url": (r.get("page") or {}).get("url") or (r.get("task") or {}).get("url"),
                 "time": (r.get("task") or {}).get("time"),
                 "uuid": r.get("_id"),
                 "title": (r.get("page") or {}).get("title"),
                 "domain": (r.get("page") or {}).get("domain")} for r in res]
        fh.write(json.dumps({"name": t["name"], "q": t["q"], "err": err,
                             "n": len(rows), "rows": rows}) + "\n")
        fh.flush()
        print("    -> %d err=%s" % (len(rows), err), file=sys.stderr, flush=True)
        if err == "RATELIMIT":
            print("    hard rate limit; sleeping 300s", file=sys.stderr, flush=True)
            time.sleep(300)
        time.sleep(8)


if __name__ == "__main__":
    main()
