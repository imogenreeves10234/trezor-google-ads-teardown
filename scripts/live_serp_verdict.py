#!/usr/bin/env python3
"""Final verdict from the corrected live-SERP sweep (fplive/)."""
import glob
import json
import os
import shutil

ROOT = "/root/workspace/trezor-ads-teardown"


def main():
    res = [json.load(open(f)) for f in glob.glob(os.path.join(ROOT, "data", "fplive", "*.json"))]
    renders, blocks, shells = [], 0, 0
    live_ads, rendered_serps = [], []
    for r in res:
        for a in r["attempts"]:
            if a.get("result") == "rendered":
                renders.append(a)
            elif a.get("result") in ("blocked", "blocked-warmup"):
                blocks += 1
            elif a.get("result") == "no-results-shell":
                shells += 1
        for s in r.get("suspicious", []):
            live_ads.append(s)
        rend = [a for a in r["attempts"] if a.get("result") == "rendered"]
        if rend:
            best = max(rend, key=lambda a: a.get("organic", 0))
            rendered_serps.append({"brand": r["brand"], "cc": r["cc"], "query": r["query"],
                                   "exit_ip": best.get("exit", {}).get("ip"),
                                   "exit_org": best.get("exit", {}).get("org"),
                                   "organic": best.get("organic"), "ads": best.get("ad_count"),
                                   "screenshot": best.get("screenshot")})
    # copy the winning screenshots into docs for display
    shotdir = os.path.join(ROOT, "docs", "assets", "live-serp")
    os.makedirs(shotdir, exist_ok=True)
    for s in rendered_serps:
        if s["screenshot"]:
            src = os.path.join(ROOT, "fpshots", s["screenshot"])
            if os.path.exists(src):
                # downscale for web
                try:
                    from PIL import Image
                    im = Image.open(src).convert("RGB")
                    im.thumbnail((1100, 3000))
                    im.save(os.path.join(shotdir, s["screenshot"].replace(".png", ".jpg")),
                            "JPEG", quality=80, optimize=True)
                    s["web_shot"] = "assets/live-serp/" + s["screenshot"].replace(".png", ".jpg")
                except Exception:
                    shutil.copy2(src, os.path.join(shotdir, s["screenshot"]))
                    s["web_shot"] = "assets/live-serp/" + s["screenshot"]
    verdict = {
        "live_phishing_ads": len(live_ads),
        "verdict": "YES" if live_ads else "NO",
        "rendered_serps": len(rendered_serps),
        "total_attempts": sum(len(r["attempts"]) for r in res),
        "blocked_attempts": blocks,
        "shell_attempts": shells,
        "queries_with_a_render": rendered_serps,
        "live_ads": live_ads,
    }
    json.dump(verdict, open(os.path.join(ROOT, "data", "live_serp_verdict.json"), "w"), indent=2)
    print(json.dumps({k: verdict[k] for k in
                      ("verdict", "live_phishing_ads", "rendered_serps", "total_attempts",
                       "blocked_attempts", "shell_attempts")}, indent=2))
    print("\nRendered SERPs (real, verified by organic-result count):")
    for s in rendered_serps:
        print(f"  {s['brand']:9} {s['cc']}  '{s['query']}'  organic={s['organic']} ads={s['ads']}  {s['exit_org']}")


if __name__ == "__main__":
    main()
