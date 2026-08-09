#!/usr/bin/env python3
"""Make working, self-contained copies of the live phishing pages for AV vaults.

For each live target it renders the page in a real browser, saves the fully
rendered DOM, and saves every resource the page loaded (js/css/images/fonts)
with correct extensions into an assets/ folder, rewriting references to local
paths so the saved index.html renders offline. Also dumps each nested payload
frame's own HTML separately.

Output: mirror/<case>/  { index.html, payload_<n>.html, assets/*, CAPTURE.json }
Real extensions on purpose - this tree is for antivirus submission, NOT for the
web-served docs/ tree.
"""
import hashlib
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(__file__))
from patchright.sync_api import sync_playwright  # noqa: E402

ROOT = "/root/workspace/trezor-ads-teardown"
OUT = os.path.join(ROOT, "mirror")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

EXT = {"javascript": ".js", "css": ".css", "html": ".html", "json": ".json",
       "png": ".png", "jpeg": ".jpg", "jpg": ".jpg", "gif": ".gif", "webp": ".webp",
       "svg": ".svg", "woff2": ".woff2", "woff": ".woff", "ttf": ".ttf", "ico": ".ico"}


def case_name(u):
    return re.sub(r"[^a-zA-Z0-9]+", "_", re.sub(r"^https?://", "", u)).strip("_")[:70]


def ext_for(url, ctype):
    ct = (ctype or "").lower()
    for k, v in EXT.items():
        if k in ct:
            return v
    p = os.path.splitext(urlparse(url).path)[1]
    return p if 0 < len(p) <= 6 else ".bin"


def mirror(target, tries=3):
    case = case_name(target)
    d = os.path.join(OUT, case)
    assets = os.path.join(d, "assets")
    os.makedirs(assets, exist_ok=True)
    meta = {"target": target, "captured": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "assets": [], "payload_frames": []}
    saved = {}  # url -> local relative path

    for attempt in range(tries):
        blobs = {}
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=f"/tmp/mir-{case[:20]}-{attempt}", channel="chrome",
                headless=False, no_viewport=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"])
            try:
                pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                collected = {}

                def on_resp(resp):
                    try:
                        u = resp.url
                        if u.startswith("data:") or u.startswith("blob:"):
                            return
                        ct = resp.headers.get("content-type", "")
                        if resp.request.resource_type in ("document",):
                            return
                        body = resp.body()
                        if body and len(body) < 6_000_000:
                            collected[u] = (body, ct)
                    except Exception:
                        pass

                ctx.on("response", on_resp)
                r = pg.goto(target, wait_until="networkidle", timeout=90000)
                meta["http_status"] = r.status if r else None
                pg.wait_for_timeout(6000)
                for _ in range(3):
                    pg.mouse.wheel(0, 1400); pg.wait_for_timeout(1200)
                meta["title"] = pg.title()
                meta["final_url"] = pg.url
                dom = pg.content()

                # nested payload frames (non Google-sandbox)
                for fr in pg.frames:
                    fu = fr.url
                    if not fu or fu in ("about:blank",) or fu == target:
                        continue
                    if re.search(r"atari-embeds|gstatic\.com|recaptcha|apis\.google\.com|"
                                 r"lh3\.googleusercontent|youtube", fu):
                        continue
                    try:
                        fh = fr.content()
                        if fh and len(fh) > 200:
                            meta["payload_frames"].append({"url": fu, "bytes": len(fh)})
                    except Exception:
                        fh = None
                    if fh:
                        blobs.setdefault("__frames__", []).append((fu, fh))

                blobs["__dom__"] = dom
                blobs["__assets__"] = collected
                ctx.close()
            except Exception as e:
                meta["error"] = str(e)[:200]
                ctx.close()
                time.sleep(3)
                continue
        if blobs.get("__dom__"):
            break

    dom = blobs.get("__dom__", "")
    collected = blobs.get("__assets__", {})
    # save assets with real extensions
    for u, (body, ct) in collected.items():
        name = hashlib.md5(u.encode()).hexdigest()[:14] + ext_for(u, ct)
        with open(os.path.join(assets, name), "wb") as f:
            f.write(body)
        saved[u] = "assets/" + name
        meta["assets"].append({"url": u, "file": name, "bytes": len(body), "content_type": ct})
    # rewrite references
    for u, rel in saved.items():
        dom = dom.replace(u, rel)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(dom)
    # payload frames as their own html
    for i, (fu, fh) in enumerate(blobs.get("__frames__", []), 1):
        with open(os.path.join(d, f"payload_{i}.html"), "w", encoding="utf-8") as f:
            f.write(fh)
        meta["payload_frames"][i - 1]["file"] = f"payload_{i}.html"
    meta["asset_count"] = len(saved)
    meta["index_bytes"] = len(dom)
    with open(os.path.join(d, "CAPTURE.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  [{case[:44]:46}] http={meta.get('http_status')} assets={len(saved)} "
          f"frames={len(meta['payload_frames'])} idx={len(dom)}B", flush=True)
    return meta


if __name__ == "__main__":
    targets = [t["url"] for t in json.load(open(os.path.join(ROOT, "data", "live_targets.json")))]
    # also mirror the two live standalone payloads directly
    targets += ["https://ksf-webapp-080826.web.app/",
                "https://japanesetoenailfunguscode.com/ledger1/v5.html"]
    if len(sys.argv) > 1:
        targets = targets[int(sys.argv[1]):int(sys.argv[2])]
    os.makedirs(OUT, exist_ok=True)
    allmeta = []
    for t in targets:
        try:
            allmeta.append(mirror(t))
        except Exception as e:
            print(f"  ERR {t}: {e}", flush=True)
    json.dump(allmeta, open(os.path.join(ROOT, "data", "mirror_meta.json"), "w"), indent=2)
