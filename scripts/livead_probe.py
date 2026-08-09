#!/usr/bin/env python3
"""Are these phishing ads LIVE in Google Search right now?

For one (geo, query) it renders the real SERP through a residential exit and
reports every sponsored result, flagging any whose displayed URL or aclk
destination points at Google-owned hosting or a known phishing domain.

A hit = a live malicious ad in that country, today. Absence across retries is
reported as "not observed in N attempts", never as "no ads".
"""
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import CONSENT, LOCALE, TZ, gonzo, slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"
SUSPECT = re.compile(
    r"sites\.google\.com|\.web\.app|firebaseapp\.com|appspot\.com|storage\.googleapis\.com|"
    r"googleusercontent|script\.google|lookerstudio|blogspot|/view/", re.I)
BRAND_DOMAINS = {
    "trezor": "trezor.io", "ledger": "ledger.com", "exodus": "exodus.com",
    "phantom": "phantom.app", "metamask": "metamask.io", "uniswap": "uniswap.org",
    "coinbase": "coinbase.com", "okx": "okx.com",
}

AD_JS = r"""
() => {
  const seen = new Set(); const res = [];
  for (const a of Array.from(document.querySelectorAll('a[href]'))) {
    const href = a.href || '';
    if (!/aclk|googleadservices\.com\/pagead\/aclk/i.test(href)) continue;
    let block = a;
    for (let i=0;i<9 && block.parentElement;i++){block=block.parentElement;
      if (block.innerText && block.innerText.length>60) break;}
    const text=(block.innerText||'').trim().slice(0,600);
    if(!text||seen.has(text.slice(0,100))) continue; seen.add(text.slice(0,100));
    let dest=null; try{const u=new URL(href);dest=u.searchParams.get('adurl')||u.searchParams.get('url');}catch(e){}
    const cite=block.querySelector('cite');
    res.push({headline:(block.querySelector('[role=heading],h3')||{}).innerText||text.split('\n')[0],
      displayed_url:cite?cite.innerText.trim():null, destination:dest, href:href.slice(0,700),
      block_text:text});
  }
  return res;
}
"""


def probe(cc, query, brand, tld, hl, tries=4):
    out = {"cc": cc, "query": query, "brand": brand, "attempts": [], "ads": [],
           "suspicious_ads": [], "status": "UNVERIFIED"}
    for a in range(1, tries + 1):
        rec = {"attempt": a}
        try:
            proxy = gonzo(cc)
            host, port, user, pw = proxy.split(":")
            rec["exit_user"] = user
            profile = f"/tmp/livead-{cc}-{random.randint(1000,99999)}"
            os.makedirs(profile, exist_ok=True)
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=profile, channel="chrome", headless=False, no_viewport=True,
                    proxy={"server": f"http://{host}:{port}", "username": user, "password": pw},
                    locale=LOCALE.get(cc, "en-US"), timezone_id=TZ.get(cc, "UTC"),
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
                try:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                    try:
                        pg.goto("https://ipinfo.io/json", timeout=40000)
                        rec["exit"] = json.loads(pg.inner_text("pre"))
                    except Exception:
                        rec["exit"] = {}
                    pg.goto(f"https://www.google.{tld}/", wait_until="domcontentloaded", timeout=70000)
                    pg.wait_for_timeout(2500)
                    for lbl in CONSENT:
                        try:
                            b = pg.get_by_role("button", name=lbl, exact=False)
                            if b.count():
                                b.first.click(timeout=4000); pg.wait_for_timeout(2000); break
                        except Exception:
                            pass
                    box = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=15000)
                    box.click()
                    for ch in query:
                        pg.keyboard.type(ch, delay=random.randint(55, 175))
                    pg.wait_for_timeout(700)
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(2500)
                    if "/sorry/" in pg.url:
                        rec["result"] = "blocked"; out["attempts"].append(rec); ctx.close(); time.sleep(3); continue
                    painted = False
                    for sel in ("#tads", "#search", "#rso", "#center_col"):
                        try:
                            pg.wait_for_selector(sel, timeout=15000, state="attached"); painted = True; break
                        except Exception:
                            continue
                    pg.wait_for_timeout(4500)
                    pg.mouse.wheel(0, 500); pg.wait_for_timeout(1500); pg.mouse.wheel(0, -300)
                    ads = pg.evaluate(AD_JS)
                    rec["result"] = "rendered"; rec["ad_count"] = len(ads); rec["painted"] = painted
                    shot = os.path.join(ROOT, "liveadshots", f"{brand}_{cc}_{slug(query)}_{a}.png")
                    os.makedirs(os.path.dirname(shot), exist_ok=True)
                    try:
                        pg.screenshot(path=shot)
                        rec["screenshot"] = os.path.basename(shot)
                    except Exception:
                        pass
                    for ad in ads:
                        blob = (ad.get("displayed_url") or "") + " " + (ad.get("destination") or "") + " " + (ad.get("href") or "")
                        ad["suspicious"] = bool(SUSPECT.search(blob))
                        ad["cc"] = cc; ad["query"] = query; ad["brand"] = brand
                        ad["attempt"] = a; ad["screenshot"] = rec.get("screenshot")
                        out["ads"].append(ad)
                        if ad["suspicious"]:
                            out["suspicious_ads"].append(ad)
                    out["attempts"].append(rec)
                    if painted:
                        out["status"] = "MALICIOUS_AD_LIVE" if out["suspicious_ads"] else "RENDERED_NO_MALICIOUS_AD"
                        break
                finally:
                    ctx.close()
        except Exception as e:
            rec["result"] = "error"; rec["error"] = str(e)[:160]; out["attempts"].append(rec)
        time.sleep(3)
    print(json.dumps({"brand": brand, "cc": cc, "q": query, "status": out["status"],
                      "ads": len(out["ads"]), "suspicious": len(out["suspicious_ads"])}), flush=True)
    return out


if __name__ == "__main__":
    idx = int(sys.argv[1])
    jobs = json.load(open(os.path.join(ROOT, "data", "livead_jobs.json")))
    j = jobs[idx]
    r = probe(j["cc"], j["query"], j["brand"], j["tld"], j["hl"])
    os.makedirs(os.path.join(ROOT, "data", "livead"), exist_ok=True)
    json.dump(r, open(os.path.join(ROOT, "data", "livead", f"{idx:03d}_{j['brand']}_{j['cc']}.json"), "w"), indent=2)
