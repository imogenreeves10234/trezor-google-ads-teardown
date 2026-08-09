#!/usr/bin/env python3
"""For each ranking phishing page: screenshot + extract its payload/backend host.

Answers 'is the backend the same for all' by recording, per page, the second-stage
host its iframe loads (the actual harvesting kit) and the page's own hash.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from serp_probe import slug  # noqa: E402
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"
IGNORE = re.compile(r"atari-embeds|gstatic\.com|recaptcha|apis\.google\.com|lh3\.googleusercontent|youtube|googletagmanager")


def main():
    pages = json.load(open(os.path.join(ROOT, "data", "ranking_pages.json")))
    # prioritise: ranked-for-query first, then custom-domain ones
    pages.sort(key=lambda p: (p["source"] != "ranked", p["attached_domain"] is None))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(pages)
    pages = pages[:limit]
    out = []
    os.makedirs(os.path.join(ROOT, "rankshots"), exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(channel="chrome", headless=False,
                               args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = br.new_context(viewport={"width": 1280, "height": 900})
        for i, pg_meta in enumerate(pages):
            u = pg_meta["url"]
            rec = {**pg_meta}
            try:
                page = ctx.new_page()
                r = page.goto(u, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(5000)
                rec["http"] = r.status if r else None
                rec["final_url"] = page.url
                rec["live"] = "accounts.google.com" not in page.url
                rec["title"] = (page.title() or "")[:120]
                body = page.evaluate("() => document.body ? document.body.innerText : ''")
                rec["signals"] = [s for s in ["recovery phrase", "seed phrase", "private key",
                                              "12 word", "24 word", "passphrase", "connect wallet",
                                              "import wallet", "restore"] if s in body.lower()]
                frames = sorted({f.url for f in page.frames if f.url and f.url != u
                                 and f.url != "about:blank" and not IGNORE.search(f.url)})
                rec["payload_frames"] = [f for f in frames if f.startswith("http")][:4]
                rec["payload_host"] = None
                for f in rec["payload_frames"]:
                    h = re.sub(r"^https?://", "", f).split("/")[0]
                    if "sites.google.com" not in h:
                        rec["payload_host"] = h; break
                rec["dom_hash"] = hashlib.sha256(re.sub(r"\s+", " ", body).strip().encode()).hexdigest()[:16]
                shot = os.path.join(ROOT, "rankshots", f"{i:02d}_{slug(u)[:50]}.png")
                page.screenshot(path=shot)
                rec["screenshot"] = os.path.basename(shot)
                page.close()
            except Exception as e:
                rec["error"] = str(e)[:120]
            print(f"  [{i}] live={rec.get('live')} payload={rec.get('payload_host') or '-':34} "
                  f"sig={len(rec.get('signals',[]))} {u[:56]}", flush=True)
            out.append(rec)
        br.close()
    json.dump(out, open(os.path.join(ROOT, "data", "ranking_captured.json"), "w"), indent=2)
    live = [r for r in out if r.get("live")]
    hosts = {}
    for r in live:
        if r.get("payload_host"):
            hosts.setdefault(r["payload_host"], 0)
            hosts[r["payload_host"]] += 1
    print(f"\ncaptured {len(out)}, live {len(live)}")
    print("distinct payload hosts:", json.dumps(hosts, indent=2))


if __name__ == "__main__":
    main()
