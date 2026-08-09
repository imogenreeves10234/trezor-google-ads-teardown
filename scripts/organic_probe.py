#!/usr/bin/env python3
"""Capture ORGANIC (unpaid) Google results and flag phishing pages that rank.

Renders a real SERP through a residential exit (ziny-first) and extracts every
organic result with its rank, title, and displayed domain, flagging any on
Google-owned hosting (sites.google.com etc.) or a known phishing host.
Screenshots the full page.

Usage: organic_probe.py <brand> <cc> "<query>" <tld> <hl> [max_attempts]
"""
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from fp_probe import get_proxy, DEVICES, LOCALE, TZ  # noqa: E402
from serp_probe import CONSENT, slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"
SUSPECT = re.compile(
    r"sites\.google\.com|\.web\.app|firebaseapp\.com|appspot\.com|storage\.googleapis\.com|"
    r"googleusercontent|script\.google|lookerstudio|blogspot\.com|translate\.goog", re.I)

ORG_JS = r"""
() => {
  const out=[]; const seen=new Set();
  const blocks = document.querySelectorAll('#rso > div, #rso .MjjYud, #search .MjjYud');
  let rank=0;
  for (const b of blocks) {
    const a = b.querySelector('a[href^="http"]:not([href*="google.com/search"])');
    const h = b.querySelector('h3');
    if (!a || !h) continue;
    const href = a.href;
    if (/google\.com\/(search|preferences|advanced)/.test(href)) continue;
    if (seen.has(href)) continue; seen.add(href);
    rank++;
    const cite = b.querySelector('cite');
    out.push({rank, title:(h.innerText||'').slice(0,140),
      href: href.slice(0,300),
      displayed: cite ? cite.innerText.trim().slice(0,120) : null});
  }
  return out;
}
"""


def run(brand, cc, query, tld, hl, maxa=8):
    out = {"brand": brand, "cc": cc, "query": query, "attempts": [],
           "organic": [], "phishing_hits": [], "status": "BLOCKED"}
    for a in range(1, maxa + 1):
        dev = random.choice(DEVICES)
        server, user, pw = get_proxy(cc)
        profile = f"/tmp/org-{brand}-{cc}-{random.randint(10000,99999)}"
        os.makedirs(profile, exist_ok=True)
        rec = {"attempt": a, "device": dev["name"]}
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=profile, channel="chrome", headless=False, no_viewport=True,
                    proxy={"server": server, "username": user, "password": pw},
                    locale=LOCALE.get(cc, "en-US"), timezone_id=TZ.get(cc, "UTC"),
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized",
                          f"--window-size={dev['w']},{dev['h']}"])
                try:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                    try:
                        pg.goto("https://ipinfo.io/json", timeout=40000)
                        rec["exit"] = json.loads(pg.inner_text("pre"))
                    except Exception:
                        rec["exit"] = {}
                    pg.goto(f"https://www.google.{tld}/", wait_until="domcontentloaded", timeout=65000)
                    pg.wait_for_timeout(random.randint(1800, 3000))
                    for lbl in CONSENT:
                        try:
                            btn = pg.get_by_role("button", name=lbl, exact=False)
                            if btn.count():
                                btn.first.click(timeout=4000); pg.wait_for_timeout(2000); break
                        except Exception:
                            pass
                    box = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=15000)
                    box.click()
                    for ch in query:
                        pg.keyboard.type(ch, delay=random.randint(55, 175))
                    pg.wait_for_timeout(700); pg.keyboard.press("Enter")
                    pg.wait_for_timeout(3500)
                    body = pg.evaluate("() => document.body ? document.body.innerText : ''")
                    if ("/sorry/" in pg.url or len(body) < 400 or
                            re.search(r"unusual traffic|not a robot|recaptcha", body, re.I)):
                        rec["result"] = "blocked"; out["attempts"].append(rec); ctx.close(); time.sleep(2); continue
                    pg.wait_for_timeout(2500)
                    pg.mouse.wheel(0, 800); pg.wait_for_timeout(1500)
                    org = pg.evaluate(ORG_JS)
                    if len(org) < 3:
                        rec["result"] = "no-results"; out["attempts"].append(rec); ctx.close(); time.sleep(2); continue
                    rec["result"] = "rendered"; rec["organic_count"] = len(org)
                    shot = os.path.join(ROOT, "orgshots", f"{brand}_{cc}_{slug(query)}.png")
                    os.makedirs(os.path.dirname(shot), exist_ok=True)
                    pg.screenshot(path=shot, full_page=True)
                    rec["screenshot"] = os.path.basename(shot)
                    for o in org:
                        blob = (o.get("href") or "") + " " + (o.get("displayed") or "")
                        if SUSPECT.search(blob):
                            o["cc"] = cc; o["query"] = query; o["screenshot"] = rec["screenshot"]
                            out["phishing_hits"].append(o)
                    out["organic"] = org
                    out["attempts"].append(rec)
                    out["status"] = "PHISHING_RANKS" if out["phishing_hits"] else "CLEAN"
                    ctx.close()
                    break
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass
        except Exception as e:
            rec["result"] = "error"; rec["error"] = str(e)[:150]; out["attempts"].append(rec)
        time.sleep(2)
    os.makedirs(os.path.join(ROOT, "data", "organic"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "organic", f"{brand}_{cc}_{slug(query)}.json"), "w"), indent=2)
    print(json.dumps({"brand": brand, "cc": cc, "q": query, "status": out["status"],
                      "phishing_ranks": [{"rank": h["rank"], "href": h["href"]} for h in out["phishing_hits"]]}), flush=True)
    return out


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
        int(sys.argv[6]) if len(sys.argv) > 6 else 8)
