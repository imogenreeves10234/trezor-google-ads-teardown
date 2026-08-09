#!/usr/bin/env python3
"""Archive every live phishing page as reportable evidence.

For each URL captures: full HTML source, HTTP response headers, the secondary
payload frame(s) and THEIR source, extracted IOCs, and a per-URL evidence sheet.

Source is written with a .txt extension so the archive cannot be double-clicked
into a working phishing kit. Nothing is altered - the bytes are the original
response bytes, byte-for-byte, with a sha256 recorded for each.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = "/root/workspace/trezor-ads-teardown"
OUT = os.path.join(ROOT, "evidence")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

SIGNALS = ["recovery phrase", "seed phrase", "secret phrase", "private key", "24 word",
           "12 word", "mnemonic", "passphrase", "import wallet", "restore wallet",
           "connect wallet", "verify_human", "wiederherstellung"]


def slug(u):
    s = re.sub(r"^https?://", "", u)
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")[:80]


def fetch(url, dest_base):
    """curl the URL, keeping headers and body separately."""
    hdr = dest_base + ".headers.txt"
    body = dest_base + ".source.txt"
    r = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "60", "-A", UA,
         "-D", hdr, "-o", body, "-w", "%{http_code}|%{size_download}|%{url_effective}", url],
        capture_output=True, text=True)
    code, size, final = (r.stdout.split("|") + ["", "", ""])[:3]
    info = {"url": url, "http_code": code, "bytes": size, "final_url": final}
    if os.path.exists(body):
        raw = open(body, "rb").read()
        info["sha256"] = hashlib.sha256(raw).hexdigest()
        txt = raw.decode("utf-8", "ignore")
        info["title"] = (re.search(r"<title[^>]*>([^<]*)", txt, re.I) or [None, ""])[1].strip()[:150]
        flat = re.sub(r"<[^>]+>", " ", txt).lower()
        info["signals"] = [s for s in SIGNALS if s in flat or s in txt.lower()]
        info["iframes"] = sorted(set(re.findall(r'(?:data-url|src)=["\'](https?://[^"\']+)["\']', txt)))[:40]
        info["forms"] = re.findall(r'<form[^>]*action=["\']([^"\']*)', txt, re.I)[:10]
        info["post_endpoints"] = sorted(set(re.findall(r"fetch\(\s*['\"]([^'\"]+)['\"]", txt)))[:10]
    return info


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = json.load(open(os.path.join(ROOT, "data", "live_targets.json")))
    # secondary payloads discovered in the geo matrix
    payloads = {
        "https://sites.google.com/view/start-trezor-suite": ["https://ksf-webapp-080826.web.app/"],
        "https://sites.google.com/view/app-ledger-com/home": ["https://japanesetoenailfunguscode.com/ledger1/v5.html"],
        "https://sites.google.com/view/app-ledger-wallet": ["https://storage.googleapis.com/ledg-leg1-20860/index.html"],
        "https://sites.google.com/view/app-uniswap-dashbroad/uniswap": ["https://storage.googleapis.com/app-uni-sww/index.html"],
    }
    manifest = []
    for t in targets:
        u = t["url"]
        d = os.path.join(OUT, slug(u))
        os.makedirs(d, exist_ok=True)
        print(f"[*] {u}", flush=True)
        entry = {"page": fetch(u, os.path.join(d, "page")), "payloads": []}
        # follow any iframe that is not Google Sites' own embed sandbox
        found = set(payloads.get(u, []))
        for fr in entry["page"].get("iframes", []):
            if re.search(r"atari-embeds|gstatic\.com|recaptcha|youtube|googletagmanager", fr):
                continue
            if fr.startswith("http") and "sites.google.com" not in fr:
                found.add(fr)
        for i, pl in enumerate(sorted(found)):
            print(f"      payload -> {pl}", flush=True)
            entry["payloads"].append(fetch(pl, os.path.join(d, f"payload{i+1}")))
            time.sleep(0.6)
        # copy the matching geo screenshots in
        shots = []
        for f in sorted(os.listdir(os.path.join(ROOT, "geoshots"))) if os.path.isdir(os.path.join(ROOT, "geoshots")) else []:
            key = re.sub(r"[^a-z0-9]+", "-", u.replace("https://sites.google.com/", "")).strip("-")[:60]
            if f.endswith(".png") and key in f:
                src = os.path.join(ROOT, "geoshots", f)
                dst = os.path.join(d, f)
                if not os.path.exists(dst):
                    subprocess.run(["cp", src, dst])
                shots.append(f)
        entry["screenshots"] = shots
        entry["url"] = u
        manifest.append(entry)
        # per-URL evidence sheet
        with open(os.path.join(d, "EVIDENCE.txt"), "w") as f:
            p = entry["page"]
            f.write(f"URL           {u}\n")
            f.write(f"Title         {p.get('title')}\n")
            f.write(f"HTTP          {p.get('http_code')}  {p.get('bytes')} bytes\n")
            f.write(f"Final URL     {p.get('final_url')}\n")
            f.write(f"SHA256        {p.get('sha256')}\n")
            f.write(f"Captured      {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
            f.write(f"Phishing signals in source: {', '.join(p.get('signals') or []) or 'none in static HTML'}\n")
            if entry["payloads"]:
                f.write("\nSECONDARY PAYLOAD FRAMES (where the harvesting UI actually lives):\n")
                for pl in entry["payloads"]:
                    f.write(f"  {pl['url']}\n")
                    f.write(f"      HTTP {pl.get('http_code')}  {pl.get('bytes')} bytes  sha256 {pl.get('sha256')}\n")
                    f.write(f"      title: {pl.get('title')}\n")
                    f.write(f"      signals: {', '.join(pl.get('signals') or []) or 'none'}\n")
                    if pl.get("post_endpoints"):
                        f.write(f"      POSTs to: {', '.join(pl['post_endpoints'])}\n")
            if shots:
                f.write(f"\nScreenshots in this folder ({len(shots)}), one per country probed:\n")
                for s in shots:
                    f.write(f"  {s}\n")
            f.write("\nNOTE: page.source.txt / payload*.source.txt are the unmodified response bytes,\n")
            f.write("stored with a .txt extension so this archive cannot be run as a working kit.\n")
        time.sleep(0.5)

    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    live = sum(1 for m in manifest if m["page"].get("http_code") == "200")
    print(f"\n[*] archived {len(manifest)} pages ({live} returned 200), "
          f"{sum(len(m['payloads']) for m in manifest)} payload frames")


if __name__ == "__main__":
    main()
