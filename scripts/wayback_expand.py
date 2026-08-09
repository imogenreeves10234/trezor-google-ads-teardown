#!/usr/bin/env python3
"""For every candidate attacker Workspace domain, ask the Wayback CDX index for every
sites.google.com path ever archived under it.  Finds pages Common Crawl never sampled."""
import json, sys, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CDX = "http://web.archive.org/cdx/search/cdx"


def cdx(prefix, tries=2):
    q = {"url": prefix, "output": "json", "collapse": "urlkey", "limit": "500"}
    u = CDX + "?" + urllib.parse.urlencode(q)
    for i in range(tries):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=40) as f:
                d = json.loads(f.read().decode() or "[]")
                return d, None
        except Exception as e:
            if i == tries - 1:
                return None, str(e)[:90]
            time.sleep(4)
    return None, "unreachable"


def main():
    doms = json.load(open(sys.argv[1]))
    outp = sys.argv[2]
    done, rows = set(), []
    try:
        prev = json.load(open(outp))
        rows = prev
        done = {r["domain"] for r in prev}
    except Exception:
        pass
    import concurrent.futures as cf

    def one(d):
        res, err = cdx(f"sites.google.com/{d}/*")
        urls = []
        if res and len(res) > 1:
            hdr = res[0]
            io, it, ist = hdr.index("original"), hdr.index("timestamp"), hdr.index("statuscode")
            for r in res[1:]:
                urls.append({"url": r[io], "ts": r[it], "status": r[ist]})
        return {"domain": d, "n": len(urls), "err": err, "urls": urls}

    todo = [d for d in doms if d not in done]
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(one, todo):
            rows.append(r)
            print(f"{r['domain']:38s} {r['n']:4d} {r['err'] or ''}", flush=True)
    json.dump(rows, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main()
