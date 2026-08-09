#!/usr/bin/env python3
"""Google SERP sponsored-result probe through a Gonzo residential exit.

Uses patchright (stealth-patched Playwright) + a human navigation path:
homepage -> consent -> type the query -> Enter.  The `num=`/`pws=` URL params
that the first attempt used are themselves a bot tell and trigger /sorry/.

Usage: serp_probe.py <CC> "<query>" <outdir> [tld] [hl]
"""
import json
import os
import random
import re
import sys
import time
import urllib.request

from patchright.sync_api import sync_playwright

LOCALE = {"US": "en-US", "GB": "en-GB", "DE": "de-DE", "FR": "fr-FR", "NL": "nl-NL",
          "ES": "es-ES", "IT": "it-IT", "CA": "en-CA", "AU": "en-AU", "IN": "en-IN",
          "BR": "pt-BR", "JP": "ja-JP", "PL": "pl-PL", "CZ": "cs-CZ", "TR": "tr-TR",
          "MX": "es-MX", "ZA": "en-ZA", "SG": "en-SG", "AE": "en-AE", "CH": "de-CH",
          "AT": "de-AT", "SE": "sv-SE", "NO": "nb-NO", "DK": "da-DK", "FI": "fi-FI",
          "BE": "nl-BE", "PT": "pt-PT", "IE": "en-IE", "NZ": "en-NZ", "UA": "uk-UA",
          "RO": "ro-RO", "HU": "hu-HU", "GR": "el-GR", "IL": "he-IL", "KR": "ko-KR",
          "ID": "id-ID", "PH": "en-PH", "TH": "th-TH", "VN": "vi-VN", "NG": "en-NG",
          "AR": "es-AR", "CL": "es-CL", "CO": "es-CO"}
TZ = {"US": "America/New_York", "GB": "Europe/London", "DE": "Europe/Berlin",
      "FR": "Europe/Paris", "NL": "Europe/Amsterdam", "ES": "Europe/Madrid",
      "IT": "Europe/Rome", "CA": "America/Toronto", "AU": "Australia/Sydney",
      "IN": "Asia/Kolkata", "BR": "America/Sao_Paulo", "JP": "Asia/Tokyo",
      "PL": "Europe/Warsaw", "CZ": "Europe/Prague", "TR": "Europe/Istanbul",
      "MX": "America/Mexico_City", "ZA": "Africa/Johannesburg", "SG": "Asia/Singapore",
      "AE": "Asia/Dubai", "CH": "Europe/Zurich", "AT": "Europe/Vienna",
      "SE": "Europe/Stockholm", "NO": "Europe/Oslo", "DK": "Europe/Copenhagen",
      "FI": "Europe/Helsinki", "BE": "Europe/Brussels", "PT": "Europe/Lisbon",
      "IE": "Europe/Dublin", "NZ": "Pacific/Auckland", "UA": "Europe/Kyiv",
      "RO": "Europe/Bucharest", "HU": "Europe/Budapest", "GR": "Europe/Athens",
      "IL": "Asia/Jerusalem", "KR": "Asia/Seoul", "ID": "Asia/Jakarta",
      "PH": "Asia/Manila", "TH": "Asia/Bangkok", "VN": "Asia/Ho_Chi_Minh",
      "NG": "Africa/Lagos", "AR": "America/Argentina/Buenos_Aires",
      "CL": "America/Santiago", "CO": "America/Bogota"}

CONSENT = ["Accept all", "Alle akzeptieren", "Tout accepter", "Alles accepteren",
           "Aceptar todo", "Accetta tutto", "Zaakceptuj wszystko", "Godkänn alla",
           "Aceitar tudo", "Godta alle", "Accepter alt", "Hyväksy kaikki",
           "Elfogadom", "Přijmout vše", "I agree", "Souhlasím", "Kabul et"]

AD_JS = r"""
() => {
  const seen = new Set(); const res = [];
  for (const a of Array.from(document.querySelectorAll('a[href]'))) {
    const href = a.href || '';
    if (!/aclk|googleadservices\.com\/pagead\/aclk/i.test(href)) continue;
    let block = a;
    for (let i = 0; i < 8 && block.parentElement; i++) {
      block = block.parentElement;
      if (block.innerText && block.innerText.length > 60) break;
    }
    const text = (block.innerText || '').trim().slice(0, 700);
    const key = text.slice(0, 120);
    if (!text || seen.has(key)) continue; seen.add(key);
    let dest = null;
    try { const u = new URL(href); dest = u.searchParams.get('adurl') || u.searchParams.get('url'); } catch(e) {}
    const cite = block.querySelector('cite');
    const h = block.querySelector('[role="heading"], h3');
    res.push({
      headline: h ? h.innerText.trim() : text.split('\n')[0],
      displayed_url: cite ? cite.innerText.trim() : null,
      destination: dest,
      href_head: href.slice(0, 600),
      block_text: text,
      y: Math.round(block.getBoundingClientRect().top + window.scrollY)
    });
  }
  return res;
}
"""


def gonzo(cc, tries=3):
    key = open("/root/.config/gonzo/key").read().strip()
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(
                "https://api.gonzoproxy.app/functions/v1/proxy-api/generate",
                data=json.dumps({"country": cc, "ttl": 72, "ttl_unit": "h",
                                 "format": "ip:port:user:pass", "count": 1}).encode(),
                headers={"x-api-key": key, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=45))
            p = (r.get("proxies") or [None])[0]
            if p:
                return p
            last = r
        except Exception as e:
            last = e
        time.sleep(3)
    raise RuntimeError(f"gonzo failed: {last!r}")


def slug(s):
    return "".join(c if c.isalnum() else "-" for c in s).lower()[:50]


def _attempt(cc, query, tld, hl, base, attempt):
    """One probe through one fresh residential exit."""
    out = {"cc": cc, "query": query, "tld": tld, "hl": hl, "attempt": attempt,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ok": False}
    proxy = gonzo(cc)
    host, port, user, pw = proxy.split(":")
    out["proxy_user"] = user
    # patchright's undetected configuration: persistent context + real Chrome,
    # no custom UA, no init scripts, no viewport override. Anything else is a tell.
    profile = os.path.join("/tmp/serp-profiles", f"{cc}-{slug(query)}-{random.randint(1000,99999)}")
    os.makedirs(profile, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile, channel="chrome", headless=False, no_viewport=True,
            proxy={"server": f"http://{host}:{port}", "username": user, "password": pw},
            locale=LOCALE.get(cc, "en-US"), timezone_id=TZ.get(cc, "America/New_York"),
            args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
        try:
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                pg.goto("https://ipinfo.io/json", timeout=45000)
                out["exit"] = json.loads(pg.inner_text("pre"))
            except Exception as e:
                out["exit"] = {"error": str(e)[:120]}

            pg.goto(f"https://www.google.{tld}/", wait_until="domcontentloaded", timeout=75000)
            pg.wait_for_timeout(2500)
            for label in CONSENT:
                try:
                    b = pg.get_by_role("button", name=label, exact=False)
                    if b.count():
                        b.first.click(timeout=4000); pg.wait_for_timeout(2500); break
                except Exception:
                    pass
            # Warm the profile with one benign search first: a brand-new profile
            # whose very first action is the target query is itself a bot tell.
            try:
                wb = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=15000)
                wb.click()
                for ch in random.choice(["weather today", "news", "time now"]):
                    pg.keyboard.type(ch, delay=random.randint(70, 160))
                pg.wait_for_timeout(random.randint(500, 1100))
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(random.randint(3500, 5500))
                pg.mouse.wheel(0, 400); pg.wait_for_timeout(1200)
                if "/sorry/" in pg.url:
                    out["blocked"] = True; out["final_url"] = pg.url
                    out["exit_reason"] = "sorry-on-warmup"; out["ad_count"] = 0
                    return out
                pg.goto(f"https://www.google.{tld}/", wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(random.randint(1500, 2800))
            except Exception:
                pass

            try:
                box = pg.wait_for_selector("textarea[name=q], input[name=q]", timeout=20000)
                box.click()
                for ch in query:
                    pg.keyboard.type(ch, delay=random.randint(60, 190))
                pg.wait_for_timeout(random.randint(600, 1400))
                pg.keyboard.press("Enter")
            except Exception as e:
                out["error"] = "typing: " + str(e)[:160]
                pg.goto(f"https://www.google.{tld}/search?q={query.replace(' ', '+')}",
                        wait_until="domcontentloaded", timeout=75000)

            # Bail out immediately on the bot wall - otherwise the paint waits
            # below burn ~2 min per dead exit and the retry loop crawls.
            pg.wait_for_timeout(2000)
            if "/sorry/" in pg.url:
                out["blocked"] = True
                out["final_url"] = pg.url
                out["exit_reason"] = "sorry-interstitial"
                out["ad_count"] = 0
                return out

            painted = False
            for sel in ("#search", "#rso", "div#center_col", "#botstuff"):
                try:
                    pg.wait_for_selector(sel, timeout=15000, state="attached")
                    painted = True
                    break
                except Exception:
                    continue
            out["painted"] = painted
            pg.wait_for_timeout(4000)
            pg.mouse.move(520, 380); pg.mouse.move(760, 640)
            try:
                pg.mouse.wheel(0, 600); pg.wait_for_timeout(1500); pg.mouse.wheel(0, -600)
            except Exception:
                pass
            pg.wait_for_timeout(2500)

            out["final_url"] = pg.url
            body = pg.evaluate("() => document.body.innerText.slice(0,4000)")
            out["blocked"] = bool(re.search(
                r"unusual traffic|not a robot|systems have detected|inhabituel|ungew\u00f6hnlich", body, re.I))
            out["page_text_head"] = body[:800]
            out["ads"] = pg.evaluate(AD_JS)
            out["ad_count"] = len(out["ads"])
            out["organic_has_trezor_io"] = "trezor.io" in body.lower()
            out["ok"] = (not out["blocked"]) and painted and len(body) > 400
            if out["ok"]:
                try:
                    pg.screenshot(path=base + ".png", full_page=False)
                except Exception:
                    pass
        except Exception as e:
            out["error"] = (out.get("error", "") + " | " + str(e)[:200]).strip(" |")
        finally:
            ctx.close()
    return out


def run(cc, query, outdir, tld="com", hl="en", tries=5):
    """Retry with a FRESH residential exit each time.

    A blocked or blank result is an exit-quality problem, not evidence that the
    geo has no ads - never record it as 'no ads found'.
    """
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"{cc}__{slug(query)}")
    history = []
    best = None
    for a in range(1, tries + 1):
        try:
            out = _attempt(cc, query, tld, hl, base, a)
        except Exception as e:
            out = {"cc": cc, "query": query, "attempt": a, "ok": False, "error": repr(e)[:300]}
        history.append({k: out.get(k) for k in
                        ("attempt", "ok", "blocked", "painted", "ad_count", "error")}
                       | {"ip": (out.get("exit") or {}).get("ip"),
                          "org": (out.get("exit") or {}).get("org")})
        best = out
        print(json.dumps({"try": a, "cc": cc, "ip": (out.get("exit") or {}).get("ip"),
                          "org": (out.get("exit") or {}).get("org"),
                          "blocked": out.get("blocked"), "painted": out.get("painted"),
                          "ads": out.get("ad_count"), "ok": out.get("ok")}), flush=True)
        if out.get("ok"):
            break
        time.sleep(4)
    best = best or {}
    best["attempts"] = history
    best["status"] = "OK" if best.get("ok") else "UNVERIFIED_EXIT_BLOCKED"
    open(base + ".json", "w").write(json.dumps(best, indent=2))
    print(json.dumps({"cc": cc, "q": query, "status": best["status"],
                      "ads": best.get("ad_count"), "tries": len(history)}))
    return best


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3],
        sys.argv[4] if len(sys.argv) > 4 else "com",
        sys.argv[5] if len(sys.argv) > 5 else "en",
        int(sys.argv[6]) if len(sys.argv) > 6 else 5)
