#!/usr/bin/env python3
"""Visit each live phishing page in a real browser and record where it takes the
victim + what code runs: full redirect chain, all script hosts, wallet-drainer /
seed-harvest signatures, POST endpoints, and any obfuscation.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"

DRAINER = ["eth_requestaccounts", "web3", "ethereum.request", "walletconnect",
           "personal_sign", "eth_sendtransaction", "solana", "phantom.solana",
           "recovery phrase", "seed phrase", "mnemonic", "private key", "12 word",
           "24 word", "passphrase", "verify_human", "atob(", "eval(", "fromcharcode",
           "wallet_", "setapprovalforall", "increaseallowance", "permit("]


def analyze(targets, out_file, tag):
    out = []
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome", headless=False,
                               args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = br.new_context(viewport={"width": 1280, "height": 900})
        for i, u in enumerate(targets):
            rec = {"url": u}
            redirects, scripts, xhr = [], set(), set()
            try:
                page = ctx.new_page()
                def _onresp(r):
                    try:
                        if r.request.resource_type == "document":
                            redirects.append({"url": str(r.url)[:200], "status": r.status})
                    except Exception:
                        pass
                def _onreq(r):
                    try:
                        rt = r.resource_type
                        if rt == "script":
                            scripts.add(str(r.url).split("?")[0][:160])
                        elif rt in ("xhr", "fetch"):
                            xhr.add(str(r.method) + " " + str(r.url).split("?")[0][:160])
                    except Exception:
                        pass
                page.on("response", _onresp)
                page.on("request", _onreq)
                r = page.goto(u, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(6000)
                try:
                    page.mouse.move(400, 300); page.mouse.wheel(0, 600); page.wait_for_timeout(2500)
                except Exception:
                    pass
                rec["final_url"] = page.url
                rec["http"] = r.status if r else None
                rec["title"] = (page.title() or "")[:120]
                html = page.content()
                low = html.lower()
                rec["redirected_offsite"] = (re.sub(r"^https?://", "", page.url).split("/")[0]
                                             != re.sub(r"^https?://", "", u).split("/")[0])
                # external (non-Google-sandbox) frames = payload
                rec["payload_frames"] = sorted({f.url for f in page.frames if f.url and f.url != u
                                                and f.url != "about:blank"
                                                and not re.search(r"atari-embeds|gstatic|recaptcha|apis\.google|lh3\.google|youtube|googletagmanager|doubleclick", f.url)})[:5]
                # external script hosts (drop Google's own)
                ext_scripts = sorted({s for s in scripts
                                      if not re.search(r"gstatic|google\.com|googleapis|googletagmanager|googlesyndication", s)})
                rec["external_scripts"] = ext_scripts[:20]
                rec["xhr_fetch"] = sorted(xhr)[:15]
                rec["form_actions"] = re.findall(r'<form[^>]*action=["\']([^"\']+)', html, re.I)[:8]
                rec["post_endpoints"] = sorted(set(re.findall(r"fetch\(\s*['\"]([^'\"]+)['\"]", html)))[:10]
                rec["drainer_signatures"] = sorted({s for s in DRAINER if s in low})
                rec["has_seed_inputs"] = bool(re.search(r'(word|mnemonic|phrase|seed)[^>]*input|input[^>]*(word|mnemonic|phrase|seed)', low))
                rec["obfuscation"] = {"eval": low.count("eval("), "atob": low.count("atob("),
                                      "fromCharCode": low.count("fromcharcode"),
                                      "hex_escape": len(re.findall(r"\\x[0-9a-f]{2}", html))}
                shot = os.path.join(ROOT, "chainshots", f"{tag}_{i:02d}_{slug(u)[:44]}.png")
                os.makedirs(os.path.dirname(shot), exist_ok=True)
                page.screenshot(path=shot)
                rec["screenshot"] = os.path.basename(shot)
                page.close()
            except Exception as e:
                rec["error"] = str(e)[:140]
            print(f"  [{tag} {i}] off={rec.get('redirected_offsite')} "
                  f"drain={len(rec.get('drainer_signatures',[]))} "
                  f"payload={rec.get('payload_frames') or '-'} {u[:52]}", flush=True)
            out.append(rec)
        br.close()
    json.dump(out, open(out_file, "w"), indent=2)
    print(f"[{tag}] wrote {len(out)} -> {out_file}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "ranking"
    if which == "ranking":
        pages = json.load(open(os.path.join(ROOT, "data", "ranking_pages.json")))
        # live custom-domain ones + the 2 ranked
        targets = [p["url"] for p in pages if p.get("attached_domain")][:24]
        analyze(targets, os.path.join(ROOT, "data", "chain_ranking.json"), "rank")
    elif which == "idn":
        targets = json.load(open(os.path.join(ROOT, "data", "idn_targets.json")))
        analyze(targets, os.path.join(ROOT, "data", "chain_idn.json"), "idn")
