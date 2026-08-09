#!/usr/bin/env python3
"""Enumerate INDEXED Google Sites phishing pages via `site:` queries on a real
SERP (residential exit), and record each result's attached Workspace domain.

Usage: site_enum.py "<site: query>" <cc> <tld>
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from fp_probe import get_proxy, DEVICES, LOCALE, TZ  # noqa: E402
from serp_probe import CONSENT, slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"

LINKS_JS = r"""
() => {
  const out=[]; const seen=new Set();
  for (const a of document.querySelectorAll('#rso a[href*="sites.google.com"], #search a[href*="sites.google.com"]')) {
    const href=a.href;
    if (seen.has(href)||!/sites\.google\.com/.test(href)) continue; seen.add(href);
    const h=a.querySelector('h3')||a.closest('div')?.querySelector('h3');
    out.push({href:href.slice(0,300), title:h?h.innerText.slice(0,140):null});
  }
  return out;
}
"""


def run(query, cc, tld, maxa=6):
    out = {"query": query, "cc": cc, "results": [], "status": "BLOCKED"}
    for a in range(1, maxa + 1):
        dev = random.choice(DEVICES)
        server, user, pw = get_proxy(cc)
        prof = f"/tmp/se-{random.randint(10000,99999)}"
        os.makedirs(prof, exist_ok=True)
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=prof, channel="chrome", headless=False, no_viewport=True,
                    proxy={"server": server, "username": user, "password": pw},
                    locale=LOCALE.get(cc, "en-US"), timezone_id=TZ.get(cc, "UTC"),
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
                try:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                    pg.goto(f"https://www.google.{tld}/", wait_until="domcontentloaded", timeout=60000)
                    pg.wait_for_timeout(2200)
                    for lbl in CONSENT:
                        try:
                            b = pg.get_by_role("button", name=lbl, exact=False)
                            if b.count():
                                b.first.click(timeout=4000); pg.wait_for_timeout(1800); break
                        except Exception:
                            pass
                    box = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=15000)
                    box.click()
                    for ch in query:
                        pg.keyboard.type(ch, delay=random.randint(45, 150))
                    pg.wait_for_timeout(600); pg.keyboard.press("Enter")
                    pg.wait_for_timeout(3500)
                    body = pg.evaluate("() => document.body ? document.body.innerText : ''")
                    if "/sorry/" in pg.url or re.search(r"unusual traffic|not a robot|recaptcha", body, re.I):
                        ctx.close(); continue
                    pg.wait_for_timeout(2000); pg.mouse.wheel(0, 900); pg.wait_for_timeout(1500)
                    links = pg.evaluate(LINKS_JS)
                    out["results"] = links; out["status"] = "OK"
                    pg.screenshot(path=os.path.join(ROOT, "orgshots", f"siteenum_{slug(query)}.png"), full_page=True)
                    ctx.close(); break
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass
        except Exception:
            pass
    for r in out["results"]:
        m = re.match(r"https://sites\.google\.com/([^/]+)/", r["href"])
        r["attached_domain"] = m.group(1) if (m and m.group(1) != "view") else None
    json.dump(out, open(os.path.join(ROOT, "data", "organic", f"enum_{slug(query)}.json"), "w"), indent=2)
    print(json.dumps({"query": query, "status": out["status"], "hits": len(out["results"])}))
    for r in out["results"]:
        print(f"  {r['href']}  [{r.get('attached_domain') or '/view/'}]")
    return out


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "GB",
        sys.argv[3] if len(sys.argv) > 3 else "co.uk")
