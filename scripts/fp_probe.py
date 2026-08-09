#!/usr/bin/env python3
"""Definitive live-ad check with a fresh, coherent fingerprint per attempt.

Every attempt = a brand-new Chrome profile (no history/cookies) + a fresh
residential exit IP + a coherent device fingerprint (UA, platform, screen,
hardwareConcurrency, deviceMemory, languages, timezone) all internally
consistent and matched to the exit country. That combination is what keeps
Google from throwing the /sorry/ interstitial.

It retries with a NEW IP+fingerprint until the SERP actually renders, then reads
every sponsored result and flags any whose displayed URL / aclk destination is
Google-owned hosting or a known phishing domain = a LIVE malicious ad.

Usage: fp_probe.py <brand> <cc> "<query>" <tld> <hl> [max_attempts]
"""
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import CONSENT, gonzo, slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"

# coherent real-device fingerprints: every field internally consistent
DEVICES = [
    {"name": "win11-chrome-1080",
     "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
     "platform": "Win32", "w": 1920, "h": 1080, "dpr": 1, "hc": 16, "mem": 8,
     "gl_v": "Google Inc. (NVIDIA)",
     "gl_r": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"name": "win11-chrome-1440",
     "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
     "platform": "Win32", "w": 2560, "h": 1440, "dpr": 1, "hc": 12, "mem": 16,
     "gl_v": "Google Inc. (AMD)",
     "gl_r": "ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"name": "win10-chrome-laptop",
     "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
     "platform": "Win32", "w": 1366, "h": 768, "dpr": 1, "hc": 8, "mem": 8,
     "gl_v": "Google Inc. (Intel)",
     "gl_r": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    {"name": "mac-chrome",
     "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
     "platform": "MacIntel", "w": 1512, "h": 982, "dpr": 2, "hc": 10, "mem": 16,
     "gl_v": "Google Inc. (Apple)", "gl_r": "ANGLE (Apple, Apple M2, OpenGL 4.1)"},
]
LOCALE = {"US": "en-US", "GB": "en-GB", "DE": "de-DE", "FR": "fr-FR", "TR": "tr-TR",
          "BR": "pt-BR", "JP": "ja-JP", "ES": "es-ES", "NL": "nl-NL", "IN": "en-IN",
          "CA": "en-CA", "AU": "en-AU", "IT": "it-IT", "PL": "pl-PL"}
TZ = {"US": "America/New_York", "GB": "Europe/London", "DE": "Europe/Berlin",
      "FR": "Europe/Paris", "TR": "Europe/Istanbul", "BR": "America/Sao_Paulo",
      "JP": "Asia/Tokyo", "ES": "Europe/Madrid", "NL": "Europe/Amsterdam",
      "IN": "Asia/Kolkata", "CA": "America/Toronto", "AU": "Australia/Sydney",
      "IT": "Europe/Rome", "PL": "Europe/Warsaw"}

SUSPECT = re.compile(
    r"sites\.google\.com|\.web\.app|firebaseapp\.com|appspot\.com|storage\.googleapis\.com|"
    r"googleusercontent|script\.google|lookerstudio|blogspot\.com|translate\.goog", re.I)

AD_JS = r"""
() => {
  const out=[]; const seen=new Set();
  for (const a of Array.from(document.querySelectorAll('a[href]'))) {
    const href=a.href||'';
    if(!/aclk|googleadservices\.com\/pagead\/aclk/i.test(href)) continue;
    let bl=a; for(let i=0;i<9&&bl.parentElement;i++){bl=bl.parentElement; if(bl.innerText&&bl.innerText.length>50)break;}
    const text=(bl.innerText||'').trim().slice(0,600); if(!text||seen.has(text.slice(0,90)))continue; seen.add(text.slice(0,90));
    let dest=null; try{const u=new URL(href);dest=u.searchParams.get('adurl')||u.searchParams.get('url');}catch(e){}
    const cite=bl.querySelector('cite');
    out.push({headline:(bl.querySelector('[role=heading],h3')||{}).innerText||text.split('\n')[0],
      displayed_url:cite?cite.innerText.trim():null,destination:dest,href:href.slice(0,600),block_text:text});
  }
  return out;
}
"""


def fp_script(dev):
    return f"""
    Object.defineProperty(navigator,'platform',{{get:()=>{dev['platform']!r}}});
    Object.defineProperty(navigator,'hardwareConcurrency',{{get:()=>{dev['hc']}}});
    Object.defineProperty(navigator,'deviceMemory',{{get:()=>{dev['mem']}}});
    try {{
      const gp=WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter=function(p){{
        if(p===37445) return {dev['gl_v']!r};
        if(p===37446) return {dev['gl_r']!r};
        return gp.call(this,p);
      }};
      if(window.WebGL2RenderingContext){{
        const g2=WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter=function(p){{
          if(p===37445) return {dev['gl_v']!r};
          if(p===37446) return {dev['gl_r']!r};
          return g2.call(this,p);
        }};
      }}
    }} catch(e){{}}
    """


def one_attempt(brand, cc, query, tld, hl, a):
    dev = random.choice(DEVICES)
    proxy = gonzo(cc)
    host, port, user, pw = proxy.split(":")
    profile = f"/tmp/fp-{brand}-{cc}-{random.randint(10000,99999)}"
    os.makedirs(profile, exist_ok=True)
    rec = {"attempt": a, "device": dev["name"], "exit_user": user}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile, channel="chrome", headless=False,
            proxy={"server": f"http://{host}:{port}", "username": user, "password": pw},
            locale=LOCALE.get(cc, "en-US"), timezone_id=TZ.get(cc, "UTC"),
            no_viewport=True,
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
            pg.wait_for_timeout(random.randint(1800, 3200))
            for lbl in CONSENT:
                try:
                    b = pg.get_by_role("button", name=lbl, exact=False)
                    if b.count():
                        b.first.click(timeout=4000); pg.wait_for_timeout(2000); break
                except Exception:
                    pass
            # straight to the query (a benign warm-up search doubles the /sorry/ exposure)
            box = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=15000)
            box.click()
            for ch in query:
                pg.keyboard.type(ch, delay=random.randint(55, 180))
            pg.wait_for_timeout(random.randint(500, 1200)); pg.keyboard.press("Enter")
            pg.wait_for_timeout(2500)
            pg.wait_for_timeout(3500)
            body = pg.evaluate("() => document.body ? document.body.innerText : ''")
            # hard block signals: /sorry/ OR inline reCAPTCHA OR unusual-traffic interstitial
            if ("/sorry/" in pg.url or
                    re.search(r"unusual traffic|not a robot|recaptcha|systems have detected|"
                              r"inhabituel|ungew\u00f6hnlich|detectado tr\u00e1fico", body, re.I) or
                    len(body) < 400):
                rec["result"] = "blocked"; return rec, []
            # positive render proof: real organic results present, not just a shell/captcha
            proof = pg.evaluate("""() => {
                const org = document.querySelectorAll('#rso a h3, #search a h3, div[data-sokoban-container] h3');
                const stats = document.querySelector('#result-stats');
                return {organic: org.length, stats: !!stats};
            }""")
            if proof["organic"] < 3 and not proof["stats"]:
                rec["result"] = "no-results-shell"; rec["organic"] = proof["organic"]; return rec, []
            pg.wait_for_timeout(2500)
            pg.mouse.wheel(0, 600); pg.wait_for_timeout(1500); pg.mouse.wheel(0, -300)
            ads = pg.evaluate(AD_JS)
            rec["result"] = "rendered"; rec["organic"] = proof["organic"]; rec["ad_count"] = len(ads)
            shot = os.path.join(ROOT, "fpshots", f"{brand}_{cc}_{slug(query)}_a{a}.png")
            os.makedirs(os.path.dirname(shot), exist_ok=True)
            pg.screenshot(path=shot, full_page=True)
            rec["screenshot"] = os.path.basename(shot)
            for ad in ads:
                blob = " ".join(str(ad.get(k) or "") for k in ("displayed_url", "destination", "href"))
                ad["suspicious"] = bool(SUSPECT.search(blob))
                ad["brand"] = brand; ad["cc"] = cc; ad["query"] = query
                ad["screenshot"] = rec["screenshot"]
            return rec, ads
        finally:
            ctx.close()


def run(brand, cc, query, tld, hl, maxa=8):
    out = {"brand": brand, "cc": cc, "query": query, "attempts": [], "ads": [],
           "suspicious": [], "status": "ALL_BLOCKED"}
    for a in range(1, maxa + 1):
        try:
            rec, ads = one_attempt(brand, cc, query, tld, hl, a)
        except Exception as e:
            rec, ads = {"attempt": a, "result": "error", "error": str(e)[:150]}, []
        out["attempts"].append(rec)
        out["ads"].extend(ads)
        sus = [x for x in ads if x.get("suspicious")]
        out["suspicious"].extend(sus)
        print(f"  [{brand}/{cc} a{a}] {rec.get('result'):16} ip={rec.get('exit',{}).get('ip','-'):15} "
              f"dev={rec.get('device','-'):18} ads={rec.get('ad_count','-')} sus={len(sus)}", flush=True)
        if sus:
            out["status"] = "MALICIOUS_AD_LIVE"; break
        if rec.get("result") == "rendered":
            out["status"] = "RENDERED_CLEAN"
            # one clean render is decisive enough for this query/geo; stop
            break
        time.sleep(2)
    os.makedirs(os.path.join(ROOT, "data", "fplive"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "fplive", f"{brand}_{cc}_{slug(query)}.json"), "w"), indent=2)
    print(json.dumps({"brand": brand, "cc": cc, "q": query, "status": out["status"],
                      "renders": sum(1 for r in out['attempts'] if r.get('result') == 'rendered'),
                      "suspicious": len(out["suspicious"])}), flush=True)
    return out


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
        int(sys.argv[6]) if len(sys.argv) > 6 else 8)
