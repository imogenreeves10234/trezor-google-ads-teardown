#!/usr/bin/env python3
"""Fetch each live phishing URL from residential exits in several countries.

Answers two things per (url, country):
  1. Does it serve at all there?  (geo-blocking / geo-gating)
  2. Is the content the SAME everywhere? (content hash -> cloaking detection)
Plus a screenshot per cell.

Usage: geo_matrix.py <cc> <outdir>   # one country, all live URLs
"""
import hashlib
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import LOCALE, TZ, gonzo  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"
SIGNALS = ["recovery phrase", "seed phrase", "secret phrase", "private key", "24 word",
           "12 word", "mnemonic", "passphrase", "import wallet", "restore wallet",
           "connect wallet", "wiederherstellung", "geheime phrase", "リカバリー"]


def slug(u):
    return re.sub(r"[^a-z0-9]+", "-", u.replace("https://sites.google.com/", "")).strip("-")[:60]


def run(cc, outdir, urls, tries=4):
    os.makedirs(outdir, exist_ok=True)
    results = []
    proxy = None
    for attempt in range(tries):
        try:
            proxy = gonzo(cc)
            break
        except Exception as e:
            print(f"[{cc}] gonzo attempt {attempt+1}: {e}", flush=True)
            time.sleep(4)
    if not proxy:
        return [{"cc": cc, "error": "no proxy"}]
    host, port, user, pw = proxy.split(":")
    profile = f"/tmp/geo-profiles/{cc}-{random.randint(1000,99999)}"
    os.makedirs(profile, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile, channel="chrome", headless=False, no_viewport=True,
            proxy={"server": f"http://{host}:{port}", "username": user, "password": pw},
            locale=LOCALE.get(cc, "en-US"), timezone_id=TZ.get(cc, "UTC"),
            args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
        try:
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            exit_info = {}
            try:
                pg.goto("https://ipinfo.io/json", timeout=45000)
                exit_info = json.loads(pg.inner_text("pre"))
            except Exception as e:
                exit_info = {"error": str(e)[:80]}
            print(f"[{cc}] exit {exit_info.get('ip')} {exit_info.get('country')} "
                  f"{exit_info.get('org','')[:40]}", flush=True)

            for u in urls:
                row = {"cc": cc, "url": u, "exit_ip": exit_info.get("ip"),
                       "exit_country": exit_info.get("country"), "exit_org": exit_info.get("org")}
                try:
                    resp = pg.goto(u, wait_until="domcontentloaded", timeout=70000)
                    pg.wait_for_timeout(6000)
                    final = pg.url
                    row["http_status"] = resp.status if resp else None
                    row["final_url"] = final
                    if "accounts.google.com" in final:
                        row["state"] = "REMOVED_OR_PRIVATE"
                    else:
                        row["state"] = "SERVED"
                    row["title"] = (pg.title() or "")[:120]
                    body = pg.evaluate("() => document.body ? document.body.innerText : ''")
                    row["text_len"] = len(body)
                    row["text_hash"] = hashlib.sha256(
                        re.sub(r"\s+", " ", body).strip().encode()).hexdigest()[:16]
                    low = body.lower()
                    row["signals"] = [s for s in SIGNALS if s in low]
                    # nested Google-owned payload frames
                    row["frames"] = sorted({f.url for f in pg.frames
                                            if f.url and "sites.google.com" not in f.url
                                            and f.url != "about:blank"})[:6]
                    shot = os.path.join(outdir, f"{cc}__{slug(u)}.png")
                    pg.screenshot(path=shot)
                    row["screenshot"] = os.path.basename(shot)
                except Exception as e:
                    row["state"] = "ERROR"
                    row["error"] = str(e)[:160]
                print(f"  [{cc}] {row['state']:18} {row.get('text_hash','-'):16} "
                      f"{u.replace('https://sites.google.com','')[:52]}", flush=True)
                results.append(row)
                time.sleep(1.5)
        finally:
            ctx.close()
    return results


if __name__ == "__main__":
    cc = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "geoshots")
    targets = [t["url"] for t in json.load(open(os.path.join(ROOT, "data", "live_targets.json")))]
    res = run(cc, outdir, targets)
    with open(os.path.join(ROOT, "data", f"geomatrix_{cc}.json"), "w") as f:
        json.dump(res, f, indent=2)
    served = sum(1 for r in res if r.get("state") == "SERVED")
    print(f"[{cc}] served {served}/{len(res)}")
