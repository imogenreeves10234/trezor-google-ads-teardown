#!/usr/bin/env python3
"""RDAP lookup for a list of domains. Reports registration/expiry and registrar.
A lookup that fails is reported as FAILED, never as 'not registered'."""
import json, sys, time, urllib.request, concurrent.futures as cf

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"


def rdap(d):
    out = {"domain": d}
    for base in ("https://rdap.org/domain/", "https://rdap.verisign.com/com/v1/domain/"):
        try:
            r = urllib.request.Request(base + d, headers={"User-Agent": UA,
                                                          "Accept": "application/rdap+json"})
            with urllib.request.urlopen(r, timeout=30) as f:
                j = json.loads(f.read().decode())
            ev = {e.get("eventAction"): e.get("eventDate") for e in j.get("events", [])}
            out["registered"] = (ev.get("registration") or "")[:10]
            out["expires"] = (ev.get("expiration") or "")[:10]
            out["changed"] = (ev.get("last changed") or "")[:10]
            reg = ""
            for e in j.get("entities", []):
                if "registrar" in (e.get("roles") or []):
                    try:
                        for it in e["vcardArray"][1]:
                            if it[0] == "fn":
                                reg = it[3]
                    except Exception:
                        pass
            out["registrar"] = reg
            out["ns"] = sorted({(n.get("ldhName") or "").lower()
                                for n in j.get("nameservers", [])})[:4]
            out["status"] = "OK"
            return out
        except urllib.error.HTTPError as e:
            out["status"] = "HTTP%d" % e.code
            if e.code == 404:
                out["status"] = "NOT_FOUND"
                return out
        except Exception as e:
            out["status"] = "FAILED:" + str(e)[:50]
        time.sleep(1)
    return out


if __name__ == "__main__":
    doms = json.load(open(sys.argv[1]))
    res = []
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for r in ex.map(rdap, doms):
            res.append(r)
            print(f"{r['domain']:34s} {r.get('status',''):12s} reg={r.get('registered','-'):10s} "
                  f"exp={r.get('expires','-'):10s} {r.get('registrar','')[:28]} {','.join(r.get('ns',[]))[:40]}",
                  flush=True)
    json.dump(res, open(sys.argv[2], "w"), indent=1)
