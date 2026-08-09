#!/usr/bin/env python3
"""Diagnose whether Google serves ANY ad to our probe sessions.

Distinguishes two very different states that both look like "0 ads":
  (a) the page has ads and our selector missed them  -> selector bug
  (b) the page has no ads at all                      -> Google withheld ads
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import CONSENT, LOCALE, TZ, gonzo, slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

CC = sys.argv[1] if len(sys.argv) > 1 else "GB"
QUERY = sys.argv[2] if len(sys.argv) > 2 else "car insurance"
TLD = sys.argv[3] if len(sys.argv) > 3 else "co.uk"

DIAG = r"""
() => {
  const body = document.body.innerText || '';
  const html = document.documentElement.outerHTML;
  const count = (re) => (html.match(re) || []).length;
  const labels = ['Sponsored','Ad','Anzeige','Annonce','Gesponsert','Publicidad','Sponsorizzato','Gesponsord'];
  const labelHits = {};
  for (const l of labels) labelHits[l] = (body.match(new RegExp('\\b'+l+'\\b','g'))||[]).length;
  return {
    body_len: body.length,
    aclk_in_html: count(/aclk/g),
    googleadservices_in_html: count(/googleadservices/g),
    data_text_ad: count(/data-text-ad/g),
    tads_container: !!document.querySelector('#tads, #tadsb, #bottomads'),
    label_hits: labelHits,
    anchors_total: document.querySelectorAll('a[href]').length,
    sample_ad_html: (document.querySelector('#tads') || {}).outerHTML ?
        document.querySelector('#tads').outerHTML.slice(0, 1500) : null,
    first_organic: (document.querySelector('#search a[href], #rso a[href]') || {}).href || null,
  };
}
"""


def main():
    proxy = gonzo(CC)
    host, port, user, pw = proxy.split(":")
    profile = f"/tmp/serp-profiles/diag-{CC}-{random.randint(1000,9999)}"
    os.makedirs(profile, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile, channel="chrome", headless=False, no_viewport=True,
            proxy={"server": f"http://{host}:{port}", "username": user, "password": pw},
            locale=LOCALE.get(CC, "en-US"), timezone_id=TZ.get(CC, "Europe/London"),
            args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
        try:
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto(f"https://www.google.{TLD}/", wait_until="domcontentloaded", timeout=75000)
            pg.wait_for_timeout(2500)
            for label in CONSENT:
                try:
                    b = pg.get_by_role("button", name=label, exact=False)
                    if b.count():
                        b.first.click(timeout=4000); pg.wait_for_timeout(2500); break
                except Exception:
                    pass
            box = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=20000)
            box.click()
            for ch in QUERY:
                pg.keyboard.type(ch, delay=random.randint(60, 170))
            pg.wait_for_timeout(900)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(3000)
            if "/sorry/" in pg.url:
                print(json.dumps({"cc": CC, "blocked": True})); return
            for sel in ("#search", "#rso", "#center_col"):
                try:
                    pg.wait_for_selector(sel, timeout=20000, state="attached"); break
                except Exception:
                    continue
            pg.wait_for_timeout(5000)
            d = pg.evaluate(DIAG)
            d["cc"] = CC; d["query"] = QUERY; d["url"] = pg.url; d["blocked"] = False
            print(json.dumps(d, indent=2)[:4000])
            out = f"/root/workspace/trezor-ads-teardown/data/addiag_{CC}_{slug(QUERY)}.json"
            open(out, "w").write(json.dumps(d, indent=2))
            pg.screenshot(path=out.replace(".json", ".png"))
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
