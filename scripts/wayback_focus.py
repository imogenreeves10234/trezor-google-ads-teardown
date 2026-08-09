#!/usr/bin/env python3
"""Focused Wayback CDX expansion with incremental (per-domain) writes so a kill never
loses work.  One JSON line per domain."""
import json, os, sys, time, urllib.parse, urllib.request
import concurrent.futures as cf

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CDX = "http://web.archive.org/cdx/search/cdx"


def cdx(prefix):
    q = {"url": prefix, "output": "json", "collapse": "urlkey", "limit": "800"}
    u = CDX + "?" + urllib.parse.urlencode(q)
    for i in range(3):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=60) as f:
                return json.loads(f.read().decode() or "[]"), None
        except Exception as e:
            err = str(e)[:80]
            time.sleep(5)
    return None, err


def one(d):
    res, err = cdx("sites.google.com/%s/*" % d)
    urls = []
    if res and len(res) > 1:
        h = res[0]
        io, it, ist = h.index("original"), h.index("timestamp"), h.index("statuscode")
        for r in res[1:]:
            urls.append({"url": r[io], "ts": r[it], "status": r[ist]})
    return {"domain": d, "n": len(urls), "err": err, "urls": urls}


def main():
    doms = json.load(open(sys.argv[1]))
    outp = sys.argv[2]
    done = set()
    if os.path.exists(outp):
        for l in open(outp):
            try:
                done.add(json.loads(l)["domain"])
            except Exception:
                pass
    fh = open(outp, "a")
    todo = [d for d in doms if d not in done]
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(one, d): d for d in todo}
        for f in cf.as_completed(futs):
            r = f.result()
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print("%-34s %4d %s" % (r["domain"], r["n"], r["err"] or ""), flush=True)


if __name__ == "__main__":
    main()
