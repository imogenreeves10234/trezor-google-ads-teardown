#!/usr/bin/env python3
"""Aggregate the live-ad SERP sweep into a single verdict."""
import glob
import json
import os
import collections

ROOT = "/root/workspace/trezor-ads-teardown"


def main():
    res = [json.load(open(f)) for f in glob.glob(os.path.join(ROOT, "data", "livead", "*.json"))]
    total = len(res)
    rendered = sum(1 for r in res if r["status"] in ("MALICIOUS_AD_LIVE", "RENDERED_NO_MALICIOUS_AD"))
    blocked = sum(1 for r in res if r["status"] == "UNVERIFIED")
    live_ads = []
    for r in res:
        for a in r.get("suspicious_ads", []):
            live_ads.append({"brand": a.get("brand"), "cc": a.get("cc"),
                             "query": a.get("query"), "displayed_url": a.get("displayed_url"),
                             "destination": (a.get("destination") or "")[:200]})
    per_brand = {}
    brands = sorted({r["brand"] for r in res})
    for b in brands:
        rb = [r for r in res if r["brand"] == b]
        geos = sorted({r["cc"] for r in rb})
        rend = [r for r in rb if r["status"] in ("MALICIOUS_AD_LIVE", "RENDERED_NO_MALICIOUS_AD")]
        live = sorted({a["cc"] for r in rb for a in r.get("suspicious_ads", [])})
        per_brand[b.capitalize()] = {"checked": len(rb), "rendered": len(rend),
                                     "geos_checked": len(geos), "live_countries": live}
    verdict = {
        "total": total, "rendered": rendered, "blocked": blocked,
        "brands": len(brands), "geos": len(sorted({r["cc"] for r in res})),
        "total_live_ads": len(live_ads), "live_ads": live_ads, "per_brand": per_brand,
    }
    json.dump(verdict, open(os.path.join(ROOT, "data", "livead_verdict.json"), "w"), indent=2)
    print(json.dumps({k: verdict[k] for k in
                      ("total", "rendered", "blocked", "brands", "geos", "total_live_ads")}, indent=2))
    for b, v in per_brand.items():
        print(f"  {b:10} rendered {v['rendered']}/{v['checked']}  live in {v['live_countries'] or 'none'}")


if __name__ == "__main__":
    main()
