#!/usr/bin/env python3
"""Cloak-aware visit: residential IP + real Chrome + Google ad referrer + gclid +
human mouse movement — the conditions a cloaked phishing page requires before it
shows the real scam. Records final URL, redirect chain, scripts, drainer
signatures, and screenshots. Compares against a plain datacenter fetch to expose
cloaking (benign to bots, malicious to real victims).
"""
import json
import os
import random
import re
import string
import sys

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"
ZINY = json.load(open("/root/.config/ziny/creds.json"))
DRAINER = ["eth_requestaccounts", "web3", "ethereum.request", "walletconnect", "personal_sign",
           "eth_sendtransaction", "solana", "recovery phrase", "seed phrase", "mnemonic",
           "private key", "12 word", "24 word", "passphrase", "verify_human", "connect wallet",
           "import wallet", "restore wallet"]
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")


def zproxy(cc="US"):
    r = ZINY["residential"]; sess = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return (f"http://{r['endpoint']}:{r['http_port']}", ZINY["username"],
            f"{r['proxy_key']}_country-{cc}_session-{sess}")


def visit(u, cc="US", mobile=False, tries=4):
    gclid = "Cj0KCQ" + "".join(random.choices(string.ascii_letters + string.digits, k=60))
    landing = u + ("&" if "?" in u else "?") + f"gclid={gclid}&gad_source=1"
    for a in range(tries):
        server, user, pw = zproxy(cc)
        prof = f"/tmp/cloak-{random.randint(10000,99999)}"
        os.makedirs(prof, exist_ok=True)
        rec = {"url": u, "cc": cc, "mobile": mobile, "attempt": a + 1}
        redirects, scripts, xhr = [], set(), set()
        try:
            with sync_playwright() as p:
                kw = dict(user_data_dir=prof, channel="chrome", headless=False,
                          proxy={"server": server, "username": user, "password": pw},
                          locale="en-US", args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
                if mobile:
                    kw.update(user_agent=MOBILE_UA, viewport={"width": 390, "height": 844},
                              is_mobile=True, has_touch=True)
                else:
                    kw.update(no_viewport=True)
                ctx = p.chromium.launch_persistent_context(**kw)
                try:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                    try:
                        pg.goto("https://ipinfo.io/json", timeout=40000)
                        rec["exit"] = json.loads(pg.inner_text("pre"))
                    except Exception:
                        rec["exit"] = {}

                    def onresp(r):
                        try:
                            if r.request.resource_type == "document":
                                redirects.append({"url": str(r.url)[:180], "status": r.status})
                        except Exception:
                            pass

                    def onreq(r):
                        try:
                            rt = r.resource_type
                            if rt == "script":
                                scripts.add(str(r.url).split("?")[0][:150])
                            elif rt in ("xhr", "fetch"):
                                xhr.add(str(r.method) + " " + str(r.url).split("?")[0][:150])
                        except Exception:
                            pass
                    pg.on("response", onresp); pg.on("request", onreq)
                    # arrive as if from a Google ad click
                    try:
                        pg.set_extra_http_headers({"Referer": "https://www.google.com/"})
                    except Exception:
                        pass
                    resp = pg.goto(landing, wait_until="domcontentloaded", timeout=60000, referer="https://www.google.com/")
                    rec["http"] = resp.status if resp else None
                    # human signals — the verify_human.php gate needs these
                    for _ in range(4):
                        pg.mouse.move(random.randint(200, 900), random.randint(200, 700))
                        pg.wait_for_timeout(600)
                    pg.wait_for_timeout(3000)
                    try:
                        pg.mouse.wheel(0, 700); pg.wait_for_timeout(1500)
                    except Exception:
                        pass
                    pg.wait_for_timeout(3000)
                    rec["final_url"] = pg.url
                    html = pg.content(); low = html.lower()
                    rec["title"] = (pg.title() or "")[:120]
                    rec["redirect_chain"] = redirects[:8]
                    real = {"ledger.com", "trezor.io", "metamask.io", "phantom.app", "exodus.com",
                            "uniswap.org", "coinbase.com", "okx.com"}
                    fhost = re.sub(r"^https?://", "", pg.url).split("/")[0].replace("www.", "")
                    rec["redirects_to_real_brand"] = fhost in real
                    rec["drainer_signatures"] = sorted({s for s in DRAINER if s in low})
                    rec["payload_frames"] = sorted({f.url for f in pg.frames if f.url and f.url != landing
                                                    and f.url != "about:blank"
                                                    and not re.search(r"atari-embeds|gstatic|recaptcha|apis\.google|lh3\.google|youtube|doubleclick|googletagmanager", f.url)})[:5]
                    rec["external_scripts"] = sorted({s for s in scripts if not re.search(r"gstatic|google|gtag", s)})[:15]
                    rec["xhr_fetch"] = sorted(xhr)[:12]
                    rec["obfuscation"] = {"eval": low.count("eval("), "atob": low.count("atob("),
                                          "hex": len(re.findall(r"\\x[0-9a-f]{2}", html))}
                    rec["ok"] = "/sorry/" not in pg.url and len(html) > 600
                    shot = os.path.join(ROOT, "cloakshots",
                                        f"{slug(u)[:40]}_{cc}{'_m' if mobile else ''}.png")
                    os.makedirs(os.path.dirname(shot), exist_ok=True)
                    pg.screenshot(path=shot, full_page=False)
                    rec["screenshot"] = os.path.basename(shot)
                    if rec["ok"]:
                        ctx.close(); return rec
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass
        except Exception as e:
            rec["error"] = str(e)[:140]
    return rec


if __name__ == "__main__":
    targets = json.load(open(os.path.join(ROOT, "data", "cloak_targets.json")))
    lo = int(sys.argv[1]); hi = int(sys.argv[2]); cc = sys.argv[3] if len(sys.argv) > 3 else "US"
    out = []
    for u in targets[lo:hi]:
        r = visit(u, cc=cc)
        print(f"  {r.get('final_url','?')[:60]:62} drain={len(r.get('drainer_signatures',[]))} "
              f"real={r.get('redirects_to_real_brand')} payload={r.get('payload_frames') or '-'}", flush=True)
        out.append(r)
    os.makedirs(os.path.join(ROOT, "data", "cloak"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "cloak", f"cloak_{lo}_{hi}_{cc}.json"), "w"), indent=2)
