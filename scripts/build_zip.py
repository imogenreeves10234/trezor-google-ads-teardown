#!/usr/bin/env python3
"""Package the captured evidence into a single ZIP for abuse reporting.

Contents per page: unmodified response bytes (.source.txt), HTTP headers,
secondary payload source, one screenshot per country probed, and an evidence
sheet. Plus a top-level README, an IOC list and a machine-readable manifest.

Source files keep a .txt extension: the archive is evidence, not a runnable kit.
"""
import glob
import hashlib
import json
import os
import shutil
import time
import zipfile

ROOT = "/root/workspace/trezor-ads-teardown"
EV = os.path.join(ROOT, "evidence")
DOCS = os.path.join(ROOT, "docs")
ZIP = os.path.join(DOCS, "trezor-google-sites-phishing-evidence.zip")


def refresh_screenshots():
    """Copy every geo screenshot into the right per-page folder."""
    import re
    n = 0
    targets = json.load(open(os.path.join(ROOT, "data", "live_targets.json")))
    for t in targets:
        u = t["url"]
        folder = re.sub(r"[^a-zA-Z0-9]+", "_",
                        re.sub(r"^https?://", "", u)).strip("_")[:80]
        d = os.path.join(EV, folder)
        if not os.path.isdir(d):
            continue
        key = re.sub(r"[^a-z0-9]+", "-", u.replace("https://sites.google.com/", "")).strip("-")[:60]
        for f in sorted(glob.glob(os.path.join(ROOT, "geoshots", f"*__{key}.png"))):
            dst = os.path.join(d, os.path.basename(f))
            if not os.path.exists(dst):
                shutil.copy2(f, dst); n += 1
    return n


def build_ioc():
    hosts = json.load(open(os.path.join(ROOT, "data", "payload_hosts.json")))
    targets = json.load(open(os.path.join(ROOT, "data", "live_targets.json")))
    eco = json.load(open(os.path.join(ROOT, "data", "ecosystem.json")))
    adv = json.load(open(os.path.join(ROOT, "data", "advertised_final.json")))
    L = []
    L.append("INDICATORS — Google Sites crypto phishing, captured %s\n" %
             time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    L.append("\n[1] LIVE GOOGLE SITES PAGES (all verified serving at capture time)\n")
    for t in targets:
        L.append(f"  {t['url']}\n        title: {t['title']}\n")
    gal = json.load(open(os.path.join(ROOT, "data", "gallery.json")))
    L.append("\n[1b] STATE OF EACH PAGE AT CAPTURE TIME\n")
    for g in sorted(gal, key=lambda x: x.get("kind") or ""):
        L.append(f"  [{(g.get('kind') or '?'):18}] {g['url']}\n")
        L.append(f"        {g.get('note') or ''}\n")
        if g.get("payload"):
            L.append(f"        payload: {g['payload']}  ({g.get('payload_state')})\n")
    L.append("\n[2] SECONDARY PAYLOAD HOSTS (where the harvesting UI is served from)\n")
    for h in hosts:
        L.append(f"  {h['state']:20} {h['url']}\n")
        if h.get("title"):
            L.append(f"      title: {h['title']}\n")
        if h.get("signals"):
            L.append(f"      signals: {', '.join(h['signals'])}\n")
    L.append("\n[3] BITCOIN — Trezor campaign, 5-7 Aug 2026\n")
    L.append("  harvest   bc1qrz33mr7tx8wrpcs2pxrvv83hqwpm907s9shkz4   73 drains, 20.93 BTC, $1,349,952\n")
    L.append("  treasury  bc1qhluxs8yfper7sxnmpgpjy9e38dx4qxpuhen5cs   27.31 BTC, unspent, multi-campaign\n")
    L.append("  held      bc1q4yc2fuexygkyl27hxkpjyrjw5al9vd7c3jkyrs   7.3966 BTC\n")
    L.append("  held      bc1qpx66w070d2x68pdv3899wksl9h9vtf7fhmkg92   1.19 BTC\n")
    L.append("\n[4] URLS WITH GOOGLE ADS CLICK PARAMETERS (proof of paid distribution)\n")
    for r in adv:
        cid = ", ".join(r.get("campaign_ids") or []) or "-"
        L.append(f"  [{r['state']:8}] campaign {cid:14} {r['base']}\n")
    L.append("\n[5] ATTACKER-VERIFIED GOOGLE WORKSPACE DOMAINS (yield sites.google.com/<domain>/ URLs)\n")
    for d in eco.get("attacker_domains", []):
        L.append(f"  {d['domain']}\n")
    return "".join(L)


README = """GOOGLE SITES CRYPTO PHISHING — EVIDENCE PACKAGE
================================================
Captured {when}

WHAT THIS IS
  Full captures of {n} phishing pages hosted on sites.google.com that impersonate
  crypto wallet and exchange brands, together with the secondary payload pages
  they load, screenshots from {g} countries, and the indicator list.

  It was assembled to support abuse reports to the impersonated brands and to
  Google, and to make the case publicly checkable.

WHY THE .txt EXTENSIONS
  Every *.source.txt file is the UNMODIFIED response body, byte for byte, with a
  sha256 recorded in the evidence sheet next to it. The .txt extension is the only
  change: it stops the archive being double-clicked into a working phishing kit,
  while preserving the evidence exactly. Nothing has been edited or redacted.

LAYOUT
  <one folder per phishing page>/
      EVIDENCE.txt          summary: URL, title, HTTP status, sha256, signals,
                            payload chain, screenshot list
      page.source.txt       the Google Sites page, unmodified
      page.headers.txt      HTTP response headers
      payloadN.source.txt   the embedded payload page(s), unmodified
      payloadN.headers.txt
      <CC>__<page>.png      screenshot, one per country probed
  INDICATORS.txt            all URLs, payload hosts, BTC addresses, campaign IDs
  manifest.json             machine-readable index

THE STRUCTURE THESE PAGES USE
  A page on sites.google.com is the outer frame. The harvesting UI is loaded into
  it in an iframe from a second host. Observed second-stage hosts include Firebase
  Hosting (*.web.app), Google Cloud Storage (storage.googleapis.com) and ordinary
  third-party domains. Several outer frames are still served by Google after their
  payload host has gone dead, so a live sites.google.com URL in here may render
  blank while remaining a live impersonation of the brand.

VERIFYING ANY OF IT YOURSELF
  sha256sum <file>                        matches the value in EVIDENCE.txt
  curl -sS -A "<a browser UA>" <the URL>  re-fetch and compare

REPORTING
  Google Sites abuse:  https://support.google.com/sites/answer/1651998
  Google Ads:          https://support.google.com/google-ads/contact/report_ad
  Safe Browsing:       https://safebrowsing.google.com/safebrowsing/report_phish/

  Full write-up: https://imogenreeves10234.github.io/trezor-google-ads-teardown/
"""


def main():
    n = refresh_screenshots()
    print(f"[*] screenshots copied: {n}")
    with open(os.path.join(EV, "INDICATORS.txt"), "w") as f:
        f.write(build_ioc())
    geos = sorted({os.path.basename(p).split("__")[0]
                   for p in glob.glob(os.path.join(ROOT, "geoshots", "*.png"))})
    pages = len(json.load(open(os.path.join(ROOT, "data", "live_targets.json"))))
    with open(os.path.join(EV, "README.txt"), "w") as f:
        f.write(README.format(when=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
                              n=pages, g=len(geos)))
    os.makedirs(DOCS, exist_ok=True)
    if os.path.exists(ZIP):
        os.remove(ZIP)
    count = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(EV):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                z.write(p, os.path.join("evidence", os.path.relpath(p, EV)))
                count += 1
    size = os.path.getsize(ZIP)
    md5 = hashlib.md5(open(ZIP, "rb").read()).hexdigest()
    sha = hashlib.sha256(open(ZIP, "rb").read()).hexdigest()
    meta = {"file": os.path.basename(ZIP), "files": count, "bytes": size,
            "mb": round(size / 1048576, 2), "md5": md5, "sha256": sha,
            "pages": pages, "geos": geos,
            "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(meta, open(os.path.join(ROOT, "data", "zip_meta.json"), "w"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
